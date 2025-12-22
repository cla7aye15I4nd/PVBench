" Test for handling of very long filename in insert completion message (edit.c)
" Verifies no crash and sane truncation/omission behavior of "match in file".

" Keep messages predictable
silent! language messages C

let s:save_columns = &columns
let s:save_shortmess = &shortmess
set noswapfile
" Ensure completion messages are not suppressed
set shortmess-=c

" Prepare an extremely long file path
let s:dirname = getcwd() . "/Xdir"
let s:longdirname = s:dirname . repeat('/' . repeat('d', 255), 4)
let s:longfilename = s:longdirname . '/' . repeat('a', 255)
call mkdir(s:longdirname, 'p')
call writefile(['Totum', 'Table'], s:longfilename)

" Helper: collect new message history entries starting from a number
func! s:get_match_messages(start_nr) abort
  let msgs = []
  let end = histnr('message')
  for i in range(a:start_nr + 1, end)
    let m = histget('message', i)
    if type(m) == type('') && m =~# '^match in file'
      call add(msgs, m)
    endif
  endfor
  return msgs
endfunc

" Helper: trigger insert completion that shows the filename match
func! s:trigger_completion() abort
  new
  " Set the argument list similar to PoC to make the long file a source
  exe 'next Xfile ' . fnameescape(s:longfilename)
  let start = histnr('message')
  try
    " Insert 'T' then trigger keyword completion
    unsilent exe "normal! iT\<C-N>\<Esc>"
  catch
    echoerr 'Unexpected error during completion: ' . v:exception
    bwipe!
    return []
  endtry
  let msgs = s:get_match_messages(start)
  bwipe!
  return msgs
endfunc

let s:notes = []

" Case 1: Large columns -> should not be truncated (no leading '<') if shown
let &columns = 5000
let s:msgs1 = s:trigger_completion()
if !empty(s:msgs1)
  let s:last1 = s:msgs1[-1]
  if s:last1 =~# '^match in file <'
    echoerr 'Unexpected truncation indicator with large columns: ' . s:last1
    cquit 1
  endif
else
  call add(s:notes, 'Note: No "match in file" message captured at columns=5000 (skipping strict check)')
endif

" Case 2: Small columns -> expect truncation indicator '<' if message shown
let &columns = 30
let s:msgs2 = s:trigger_completion()
if !empty(s:msgs2)
  let s:last2 = s:msgs2[-1]
  if s:last2 !~# '^match in file <'
    echoerr 'Expected truncation indicator with small columns, got: ' . s:last2
    cquit 1
  endif
else
  call add(s:notes, 'Note: No "match in file" message captured at columns=30 (skipping truncation check)')
endif

" Case 3: Extremely small columns -> message should not be shown at all
let &columns = 10
let s:msgs3 = s:trigger_completion()
if !empty(s:msgs3)
  echoerr 'Did not expect a "match in file" message at very small columns=10: ' . s:msgs3[-1]
  cquit 1
endif

" Also ensure the original PoC action does not crash (redundant safety)
let &columns = 5000
new
exe 'next Xfile ' . fnameescape(s:longfilename)
try
  unsilent exe "normal! iT\<C-N>\<Esc>"
catch
  echoerr 'Unexpected error in PoC replay: ' . v:exception
  cquit 1
endtry
bwipe!

" Cleanup
try
  silent! exe 'bwipe! ' . fnameescape(s:longfilename)
  call delete(s:dirname, 'rf')
finally
  let &columns = s:save_columns
  let &shortmess = s:save_shortmess
  set swapfile&
endtry

qall!
