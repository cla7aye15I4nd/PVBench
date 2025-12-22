" Test for xxd buffer overflow fix when writing colored output to buffer
" This test verifies that colored output (-Ralways) with large column width
" and grouping does not overflow and matches the non-colored output when ANSI
" escapes are stripped. It also exercises the -d flag and a very large offset
" via -o.

if !has('unix')
  echo 'skipped: Unix-only test'
  qall!
endif

if !executable('xxd')
  echo 'skipped: xxd not found in PATH'
  qall!
endif

let cols = 256
let data = repeat('A', cols)
" Write exactly 256 bytes without a trailing newline
call writefile([data], 'Xxdin', 'b')

let base_args = ' -g1 -c' . cols . ' -d -o 9223372036854775808 Xxdin'

try
  let out_color = system('xxd -Ralways' . base_args)
  let out_plain = system('xxd -Rnever' . base_args)
catch
  echoerr 'Unexpected error running xxd: ' . v:exception
  call delete('Xxdin')
  cquit 1
endtry

" Strip ANSI SGR escapes from colored output
let out_color_stripped = substitute(out_color, '\%x1b\[[0-9;]*m', '', 'g')

if out_color_stripped != out_plain
  " For debugging, write outputs to files
  call writefile(split(out_color, "\n", 1), 'Xxd_out_color.raw')
  call writefile(split(out_color_stripped, "\n", 1), 'Xxd_out_color_stripped')
  call writefile(split(out_plain, "\n", 1), 'Xxd_out_plain')
  echoerr 'Colored output (stripped) does not match plain output'
  call delete('Xxdin')
  cquit 1
endif

" Edge case: ensure it also works when input is larger than one line (257 bytes)
let data2 = repeat('A', cols) . 'B'
call writefile([data2], 'Xxdin2', 'b')
let base_args2 = ' -g1 -c' . cols . ' -d -o 9223372036854775808 Xxdin2'
try
  let out_color2 = system('xxd -Ralways' . base_args2)
  let out_plain2 = system('xxd -Rnever' . base_args2)
catch
  echoerr 'Unexpected error running xxd on larger input: ' . v:exception
  call delete('Xxdin')
  call delete('Xxdin2')
  cquit 1
endtry
let out_color_stripped2 = substitute(out_color2, '\%x1b\[[0-9;]*m', '', 'g')
if out_color_stripped2 != out_plain2
  call writefile(split(out_color2, "\n", 1), 'Xxd_out_color2.raw')
  call writefile(split(out_color_stripped2, "\n", 1), 'Xxd_out_color2_stripped')
  call writefile(split(out_plain2, "\n", 1), 'Xxd_out_plain2')
  echoerr 'Colored output (stripped) does not match plain output for 257 bytes'
  call delete('Xxdin')
  call delete('Xxdin2')
  cquit 1
endif

" Clean up
call delete('Xxdin')
call delete('Xxdin2')

qall!
