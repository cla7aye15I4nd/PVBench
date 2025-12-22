" Test for early initialization of --log handling (#1097)
" The fix splits common initialization into two parts and calls the first
" part before scanning --log. This ensures required buffers are allocated
" and Vim reports a proper error instead of crashing when --log points to
" an invalid path early during startup.

" Helper: run a shell command and return [output, exit_code]
function! s:Run(cmd) abort
  let l:out = system(a:cmd)
  let l:code = v:shell_error
  return [l:out, l:code]
endfunction

let s:exe = shellescape(v:progpath)

" Detect if this Vim supports the --log option; if not, skip the test.
function! s:HasLog() abort
  let l:out = system(s:exe . ' --help 2>&1')
  if l:out =~# '\v(^|\s)--log(\s|$)'
    return 1
  endif
  let l:out2 = system(s:exe . ' -h 2>&1')
  return l:out2 =~# '\v(^|\s)--log(\s|$)'
endfunction

if !s:HasLog()
  " Feature not available in this build; skip silently.
  qall!
endif

" 1) --log with a file under a non-existent directory: should not crash and
"    should report an error (message content may vary across platforms).
let nonexist_dir = tempname() . '_no_dir'
let log_in_nonexist = nonexist_dir . '/Xlogfile'
let cmd1 = s:exe . ' -e -s -N -u NONE --log ' . shellescape(log_in_nonexist) . ' -c qall! 2>&1'
let [out1, code1] = s:Run(cmd1)
" Check for crash-like exit (commonly >=128 on Unix) or deadly signal text.
if code1 >= 128 || out1 =~? 'deadly signal' || out1 =~? 'segmentation fault'
  echoerr 'Crash when using --log with non-existent directory. exit=' . code1 . ' out=' . out1
  cquit 1
endif
" Expect some error output and certainly not an unknown option.
if out1 ==# '' || out1 =~? 'Unknown option'
  echoerr 'Expected an error about opening log file (non-existent dir). Got: ' . out1
  cquit 1
endif

" 2) --log pointing to an existing directory: should not crash and
"    should also report an error about opening/creating the file.
let dirpath = tempname() . '_dir'
call mkdir(dirpath)
let cmd2 = s:exe . ' -e -s -N -u NONE --log ' . shellescape(dirpath) . ' -c qall! 2>&1'
let [out2, code2] = s:Run(cmd2)
if code2 >= 128 || out2 =~? 'deadly signal' || out2 =~? 'segmentation fault'
  echoerr 'Crash when using --log with a directory path. exit=' . code2 . ' out=' . out2
  cquit 1
endif
if out2 ==# '' || out2 =~? 'Unknown option'
  echoerr 'Expected an error when log path is a directory. Got: ' . out2
  cquit 1
endif

" Cleanup
call delete(dirpath, 'd')

qall!
