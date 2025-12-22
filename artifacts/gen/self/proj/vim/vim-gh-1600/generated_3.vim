" Test for safe display of "match in file" with very long filenames during insert completion
" This verifies no crash and correct cropping behavior introduced in patch 530.

let s:save_columns = &columns
let s:save_more = &more
let s:save_sw = &swapfile
let s:save_complete = &complete
set nomore
set noswapfile

" Build a deeply nested very long path and a file containing words starting with 'T'
let s:dirname = getcwd() . "/Xdir"
let s:longdirname = s:dirname . repeat('/' . repeat('d', 255), 4)
let s:longfilename = s:longdirname . '/' . repeat('a', 255)

" Helper to finish with error
function! s:Fail(msg)
  echoerr a:msg
  cquit 1
endfunction

" Ensure cleanup happens at the end
function! s:Cleanup()
  try
    silent! bwipe!
    if bufexists(fnamemodify(s:longfilename, ':p'))
      execute 'silent! bwipe! ' . fnameescape(fnamemodify(s:longfilename, ':p'))
    endif
  catch
  endtry
  call delete(s:dirname, 'rf')
  let &columns = s:save_columns
  let &more = s:save_more
  let &swapfile = s:save_sw
  let &complete = s:save_complete
endfunction

" Prepare filesystem
try
  call mkdir(s:longdirname, 'p')
  call writefile(['Totum', 'Table'], s:longfilename)
catch
  call s:Cleanup()
  call s:Fail('Failed to prepare long file: ' . v:exception)
endtry

" Load the long file to make its words available from another buffer
try
  execute 'edit ' . fnameescape(s:longfilename)
catch
  call s:Cleanup()
  call s:Fail('Failed to edit long file buffer: ' . v:exception)
endtry

" Ensure other buffers are considered for completion
set complete=.,w,b,u,t

" Switch to a different buffer for doing completion (so match is from other file)
enew

function! s:GetMessagesLines()
  return split(execute('messages'), "\n")
endfunction

function! s:CountMatchInFile()
  let l:cnt = 0
  for l:line in s:GetMessagesLines()
    if l:line =~# 'match in file'
      let l:cnt += 1
    endif
  endfor
  return l:cnt
endfunction

function! s:LastMatchInFile()
  let l:last = ''
  for l:line in s:GetMessagesLines()
    if l:line =~# 'match in file'
      let l:last = l:line
    endif
  endfor
  return l:last
endfunction

function! s:DoCompletionOnce()
  try
    execute "normal! iT\<C-N>\<Esc>"
  catch
    call s:Cleanup()
    call s:Fail('Unexpected error during completion: ' . v:exception)
  endtry
endfunction

" Scenario 1: Large columns - message should appear without truncation marker '<'
let &columns = 5000
let s:before1 = s:CountMatchInFile()
call s:DoCompletionOnce()
let s:after1 = s:CountMatchInFile()
if s:after1 != s:before1 + 1
  call s:Cleanup()
  call s:Fail('Scenario 1: expected one "match in file" message to be added')
endif
let s:last1 = s:LastMatchInFile()
if s:last1 !~# 'match in file'
  call s:Cleanup()
  call s:Fail('Scenario 1: did not find "match in file" in messages')
endif
if s:last1 =~# '<'
  call s:Cleanup()
  call s:Fail('Scenario 1: truncation marker "<" unexpectedly shown for large columns')
endif

" Scenario 2: Small but positive space - expect truncation with '<'
let &columns = 30
enew
let s:before2 = s:CountMatchInFile()
call s:DoCompletionOnce()
let s:after2 = s:CountMatchInFile()
if s:after2 != s:before2 + 1
  call s:Cleanup()
  call s:Fail('Scenario 2: expected one additional "match in file" message')
endif
let s:last2 = s:LastMatchInFile()
if s:last2 !~# 'match in file <'
  call s:Cleanup()
  call s:Fail('Scenario 2: expected truncation marker "<" not found in last message: ' . s:last2)
endif

" Scenario 3: Extremely small columns - expect no message (space <= 0)
let &columns = 8
enew
let s:before3 = s:CountMatchInFile()
call s:DoCompletionOnce()
let s:after3 = s:CountMatchInFile()
if s:after3 != s:before3
  call s:Cleanup()
  call s:Fail('Scenario 3: message should not be shown when no space is available')
endif

" Final cleanup and exit
call s:Cleanup()
qall!
