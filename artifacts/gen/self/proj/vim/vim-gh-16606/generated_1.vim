" Test for early initialization of IObuff/NameBuff before processing --log and --startuptime
" The patch splits common_init() into common_init_1() and common_init_2(),
" and calls common_init_1() before scanning --startuptime/--log so buffers
" are allocated. Previously, using these options with an invalid path could
" access uninitialized buffers and crash. This test verifies:
"  - Using --startuptime with a non-existent directory does not crash
"  - Using --log with a non-existent directory does not crash (if supported)
"  - Using --startuptime with a valid temp file creates a non-empty file
"  - Using --log with a valid temp file creates the file (if supported)

set nomore

function! s:RunVim(args) abort
  " Run a child Vim with the given args, capture combined stderr/stdout
  let cmd = v:progpath . ' -e -s -N -u NONE ' . a:args . ' -c qall! 2>&1'
  let out = system(cmd)
  let status = v:shell_error
  return [status, out]
endfunction

function! s:NonexistentFile() abort
  let d = tempname()
  " Ensure it does not exist as file or dir
  if filereadable(d)
    call delete(d)
  elseif isdirectory(d)
    call delete(d, 'd')
  endif
  return d . '/Xfile'
endfunction

function! s:IsCrashExit(code) abort
  " On Unix-like systems, crash due to signal typically sets exit code >= 128
  return a:code >= 128
endfunction

" 1) --startuptime with non-existent directory should not crash
let nonexist_st = s:NonexistentFile()
let [st_status, st_out] = s:RunVim('--startuptime ' . shellescape(nonexist_st))
if s:IsCrashExit(st_status)
  echoerr '--startuptime with non-existent path crashed. Exit status: ' . st_status . ' Output: ' . st_out
  cquit 1
endif

" Optionally check for a sensible error message (not required for pass)
if st_out ==# ''
  " Some environments might suppress messages; that's OK
else
  " Accept common failure phrases; don't hard-require exact text
  if st_out !~? 'open\|file\|cannot\|can\'t'
    " Not failing the test on message mismatch, but ensure it's not a crash
  endif
endif

" 2) --log with non-existent directory should not crash (only if supported)
if has('channel')
  let nonexist_log = s:NonexistentFile()
  let [lg_status, lg_out] = s:RunVim('--log ' . shellescape(nonexist_log))
  if s:IsCrashExit(lg_status)
    echoerr '--log with non-existent path crashed. Exit status: ' . lg_status . ' Output: ' . lg_out
    cquit 1
  endif
endif

" 3) --startuptime with a valid temp file should succeed and create a non-empty file
let stfile = tempname()
call delete(stfile)
let [ok_status, ok_out] = s:RunVim('--startuptime ' . shellescape(stfile))
if s:IsCrashExit(ok_status)
  echoerr 'Crash for --startuptime with writable temp file. Output: ' . ok_out
  cquit 1
endif
if !filereadable(stfile)
  echoerr 'Startuptime file was not created: ' . stfile . ' Output: ' . ok_out
  cquit 1
endif
if getfsize(stfile) <= 0
  echoerr 'Startuptime file is empty: ' . stfile
  cquit 1
endif
call delete(stfile)

" 4) --log with a valid temp file should succeed and create the file (if supported)
if has('channel')
  let logfile = tempname()
  call delete(logfile)
  let [lg2_status, lg2_out] = s:RunVim('--log ' . shellescape(logfile))
  if s:IsCrashExit(lg2_status)
    echoerr 'Crash for --log with writable temp file. Output: ' . lg2_out
    cquit 1
  endif
  if !filereadable(logfile)
    echoerr 'Log file was not created: ' . logfile . ' Output: ' . lg2_out
    cquit 1
  endif
  call delete(logfile)
endif

qall!
