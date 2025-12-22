" Comprehensive test for Visual state reset and safe char access after :all with virtualedit=all
" This verifies fixes in:
" - arglist.c: reset_VIsual_and_resel() in :all
" - misc1.c: gchar_pos() guard when pos->col > line length
" - ops.c: charwise_block_prep() avoid pointer past line end

set belloff=all
set virtualedit=all

try
  " Prepare two argument buffers and open them in windows
  args Xa Xb
  all

  " Window 1 (Xa): three empty lines and place cursor on line 3
  call setline(1, ['', '', ''])
  call cursor(3, 1)

  " Go to window 2 (Xb) and set content
  wincmd w
  call setline(1, 'foobar')

  " Create a characterwise Visual selection that starts beyond end of line
  " and extends to column 0
  normal! $lv0

  " Running :all should reset Visual state and resel, avoiding stale pointers
  all

  " Put with indent adjustment which previously could crash due to invalid
  " Visual/cursor state
  call setreg('"', 'baz')
  try
    normal! [P
  catch
    echoerr 'Unexpected error during [P: ' . v:exception
    cquit 1
  endtry

  " Also try to repeat last Visual selection; it may give an error if Visual
  " was cleared, which is fine. It must not crash.
  try
    normal! gv
  catch
    " No previous Visual selection: acceptable, continue.
  endtry

  " Switch back to window 1 and test charwise operation when startcol > line len
  wincmd w
  call setline(1, 'x')
  " Move to end, then two virtual columns to the right, start Visual, go to start
  normal! $2lv0
  " Deleting such a selection used to risk reading past line end. It should not
  " crash and should delete the single character, leaving an empty line.
  try
    normal! "_d
  catch
    echoerr 'Unexpected error during visual delete: ' . v:exception
    cquit 1
  endtry
  let l = getline(1)
  if l !=# ''
    echoerr 'Expected empty line after deleting selection including virtual spaces, got: ' . string(l)
    cquit 1
  endif

  " Extra edge: repeat a similar operation on an empty line to ensure
  " gchar_pos() safely returns NUL past end of line, and no crash occurs.
  call setline(1, '')
  " Place cursor at column far beyond EOL and attempt a harmless motion and put
  call cursor(1, 1)
  normal! 10l
  try
    " Yank a zero-width selection by entering and exiting Visual; then put text
    normal! v<Esc>
    call setreg('"', 'Q')
    normal! p
  catch
    echoerr 'Unexpected error during operations on empty line past EOL: ' . v:exception
    cquit 1
  endtry
  if getline(1) !~# 'Q'
    echoerr 'Expected to see put text on empty line, got: ' . string(getline(1))
    cquit 1
  endif

  " Cleanup
  set virtualedit=
  silent! bw! Xa Xb
catch
  echoerr 'Unexpected error in test: ' . v:exception
  cquit 1
endtry
qall!
