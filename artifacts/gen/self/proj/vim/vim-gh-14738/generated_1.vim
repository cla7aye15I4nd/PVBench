" Test for xxd buffer overflow fix with colored output and long lines
" This verifies that xxd no longer overflows its internal line buffer when
" producing very long colored lines (e.g. with -Ralways/-R always, -g1, -c256,
" decimal address -d and a very large -o).

" Helper: robustly run xxd with the requested color mode ("always" or "never").
" Some builds accept "-Ralways" while others accept "-R always".
function! s:RunXXD(colormode, args, input) abort
  let l:base = a:args
  let l:cmd1 = 'xxd -R' . a:colormode . ' ' . l:base
  let l:out = system(l:cmd1, a:input)
  let l:status = v:shell_error
  if l:status != 0
    let l:cmd2 = 'xxd -R ' . a:colormode . ' ' . l:base
    let l:out = system(l:cmd2, a:input)
    let l:status = v:shell_error
    let l:cmd = l:cmd2
  else
    let l:cmd = l:cmd1
  endif
  return {'out': l:out, 'status': l:status, 'cmd': l:cmd}
endfunction

function! s:HasAnsiColor(str) abort
  return match(a:str, "\x1b\[[0-9;]\+m") >= 0
endfunction

" Main test
try
  if executable('xxd') == 0
    " xxd not available, skip test gracefully
    echo 'skipped: xxd not found in PATH'
    qall!
  endif

  " Ensure colorization is not disabled by environment
  if exists('$NO_COLOR')
    unlet $NO_COLOR
  endif

  let s:input = repeat('A', 256)
  let s:args = '-g1 -c256 -d -o 9223372036854775808'

  " 1) Run with colors forced: should not crash and should contain ANSI codes
  let s:res_color = s:RunXXD('always', s:args, s:input)
  if s:res_color.status != 0
    echoerr 'xxd colored run failed (exit ' . s:res_color.status . '), cmd: ' . s:res_color.cmd
    cquit 1
  endif

  let s:out = s:res_color.out
  if empty(s:out)
    echoerr 'xxd colored run produced no output'
    cquit 1
  endif

  let s:firstline = split(s:out, "\n")[0]

  " Expect a decimal address prefix (possibly negative) followed by colon+space
  if s:firstline !~ '^\d\+: ' && s:firstline !~ '^-' . '\d\+: '
    echoerr 'Unexpected address prefix in colored output: ' . s:firstline[:80]
    cquit 1
  endif

  if !s:HasAnsiColor(s:firstline)
    echoerr 'Colored run does not contain ANSI color sequences'
    cquit 1
  endif

  " The fix increases LLEN to accommodate very long colored lines.
  " With -g1 -c256 we expect a very long first line; assert a conservative minimum.
  if strlen(s:firstline) < 6000
    echoerr 'First line unexpectedly short (len=' . strlen(s:firstline) . ')'
    cquit 1
  endif

  " 2) Run with colors disabled explicitly: should not crash and must not contain ANSI
  let s:res_nocolor = s:RunXXD('never', s:args, s:input)
  if s:res_nocolor.status != 0
    echoerr 'xxd no-color run failed (exit ' . s:res_nocolor.status . '), cmd: ' . s:res_nocolor.cmd
    cquit 1
  endif

  let s:nc_out = s:res_nocolor.out
  if empty(s:nc_out)
    echoerr 'xxd no-color run produced no output'
    cquit 1
  endif

  let s:nc_first = split(s:nc_out, "\n")[0]
  if s:nc_first !~ '^\d\+: ' && s:nc_first !~ '^-' . '\d\+: '
    echoerr 'Unexpected address prefix in no-color output: ' . s:nc_first[:80]
    cquit 1
  endif

  if s:HasAnsiColor(s:nc_first)
    echoerr 'No-color run unexpectedly contains ANSI color sequences'
    cquit 1
  endif

  " 3) Sanity: colored line should be considerably longer than non-colored
  if strlen(s:firstline) <= strlen(s:nc_first)
    echoerr 'Colored output not longer than non-colored output (unexpected)'
    cquit 1
  endif

catch
  echoerr 'Unexpected error: ' . v:exception
  cquit 1
endtry

qall!
