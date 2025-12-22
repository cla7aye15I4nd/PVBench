" Test for heap buffer overflow and message handling when showing
" "match in file" for very long filenames (patch 530)
" Verifies:
"  - No crash when completing with an extremely long filename
"  - Message is added only if there is room (space > 0)
"  - Message length is bounded by IOSIZE (<= 1023)
"  - For moderate width the message indicates trimming with '<'

silent! language messages C
set nocompatible
set encoding=utf-8
set noswapfile

let s:IOSIZE_MAX = 1023

let s:save_columns = &columns
let s:save_swapfile = &swapfile
let s:save_complete = &complete

" Ensure completion searches unloaded files from the argument list
if &complete !~# 'u'
  set complete+=u
endif

function! s:GetMessages() abort
  let m = ''
  redir => m
  silent messages
  redir END
  return m
endfunction

function! s:CountOcc(haystack, pat) abort
  let cnt = 0
  for l in split(a:haystack, "\n")
    if l =~ a:pat
      let cnt += 1
    endif
  endfor
  return cnt
endfunction

function! s:LastLine(haystack, pat) abort
  let last = ''
  for l in split(a:haystack, "\n")
    if l =~ a:pat
      let last = l
    endif
  endfor
  return last
endfunction

function! s:TriggerCompletion(longfilename) abort
  " Set argument list to include a dummy and the long file, and edit the dummy
  new
  try
    execute 'next Xfile ' . fnameescape(a:longfilename)
  catch
    echoerr 'Failed to set arglist: ' . v:exception
    cquit 1
  endtry
  " This used to cause heap-buffer-overflow when displaying filename
  try
    execute "normal! iT\<C-N>"
  catch
    echoerr 'Unexpected error during completion: ' . v:exception
    cquit 1
  endtry
endfunction

" Create an extremely long path and file with words to be found by completion
let s:dirname = getcwd() . '/Xdir'
let s:longdirname = s:dirname . repeat('/' . repeat('d', 255), 4)
let s:longfilename = s:longdirname . '/' . repeat('a', 255)
call mkdir(s:longdirname, 'p')
call writefile(['Totum', 'Table'], s:longfilename)

" Test 1: Large &columns should not overflow internal buffer; a message should
"         be produced and its length must be bounded by IOSIZE.
set columns=5000
let before1 = s:GetMessages()
call s:TriggerCompletion(s:longfilename)
let after1 = s:GetMessages()
let c_before1 = s:CountOcc(before1, '^match in file')
let c_after1  = s:CountOcc(after1,  '^match in file')
if c_after1 <= c_before1
  echoerr 'Expected a "match in file" message for large columns, but none was added'
  cquit 1
endif
let last1 = s:LastLine(after1, '^match in file')
if last1 == ''
  echoerr 'Failed to capture the last "match in file" message for large columns'
  cquit 1
endif
if strlen(last1) > s:IOSIZE_MAX
  echoerr 'Message too long for IOSIZE limit: ' . strlen(last1)
  cquit 1
endif

" Clean up buffers from previous step
silent! bwipe!

" Test 2: Very small &columns should suppress the message entirely (space <= 0)
set columns=10
let before2 = s:GetMessages()
call s:TriggerCompletion(s:longfilename)
let after2 = s:GetMessages()
let c_before2 = s:CountOcc(before2, '^match in file')
let c_after2  = s:CountOcc(after2,  '^match in file')
if c_after2 != c_before2
  echoerr '"match in file" message should be suppressed for very small columns'
  cquit 1
endif

silent! bwipe!

" Test 3: Moderate &columns should show a trimmed message starting with '<'
set columns=40
let before3 = s:GetMessages()
call s:TriggerCompletion(s:longfilename)
let after3 = s:GetMessages()
let c_before3 = s:CountOcc(before3, '^match in file')
let c_after3  = s:CountOcc(after3,  '^match in file')
if c_after3 <= c_before3
  echoerr 'Expected a "match in file" message for moderate columns'
  cquit 1
endif
let last3 = s:LastLine(after3, '^match in file')
if last3 !~ '^match in file <'
  echoerr 'Expected trimmed indicator "<" for moderate columns, got: ' . last3
  cquit 1
endif
if strlen(last3) > s:IOSIZE_MAX
  echoerr 'Message too long for IOSIZE limit (moderate columns): ' . strlen(last3)
  cquit 1
endif

" Cleanup
try
  silent! bwipe!
  silent! exe 'bwipe! ' . fnameescape(s:longfilename)
catch
endtry
call delete(s:dirname, 'rf')
let &columns = s:save_columns
let &swapfile = s:save_swapfile
let &complete = s:save_complete
qall!
