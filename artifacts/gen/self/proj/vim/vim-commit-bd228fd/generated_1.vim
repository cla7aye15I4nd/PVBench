" Test for overflow fix in help.c (patch 3669)
" The patch replaced unsafe STRCPY with bounded vim_snprintf when
" constructing the search pattern for certain backslash-prefixed
" help arguments. Extremely long arguments previously could overflow
" and crash. These tests ensure that very long arguments no longer
" crash and that Vim reports E149 (no help for …) for nonsensical topics.

function! s:ExpectHelpE149(arg) abort
  try
    exe 'help ' . a:arg
    " If it succeeds unexpectedly, it's a failure for this specific case
    echoerr 'Expected E149 for "help ' . a:arg . '", but no error was thrown'
    cquit 1
  catch
    if v:exception !~# 'E149:'
      echoerr 'Expected E149 for "help ' . a:arg . '", got: ' . v:exception
      cquit 1
    endif
  endtry
endfunction

function! s:HelpNoCrashOrE149(arg) abort
  try
    exe 'help ' . a:arg
  catch
    if v:exception !~# 'E149:'
      echoerr 'Unexpected error for "help ' . a:arg . '": ' . v:exception
      cquit 1
    endif
  endtry
endfunction

" Original PoC: very long argument starting with \% must raise E149
call s:ExpectHelpE149('\%' . repeat('0', 1021))

" Much longer than IOSIZE to ensure truncation is handled safely; should be E149
call s:ExpectHelpE149('\%' . repeat('0', 4096))

" Exercise other code paths gated by vim_strchr("%_z@", arg[1])
" For these, accept either success (topic unexpectedly exists) or E149, but no crash
call s:HelpNoCrashOrE149('\@=' . repeat('x', 2000))
call s:HelpNoCrashOrE149('\z' . repeat('y', 3000))

" If we got here, all checks passed without crash and with acceptable outcomes
qall!
