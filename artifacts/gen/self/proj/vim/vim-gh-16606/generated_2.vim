" Test for early initialization split into common_init_1() and common_init_2()
" Ensure options processed very early (--startuptime, --log) don't crash and
" behave sensibly when given valid/invalid paths.

" Helper: run a fresh Vim process with supplied arguments, capture output.
func! s:RunVim(args) abort
  let cmd = v:progpath .. ' -Nu NONE -i NONE -n -N -e -s ' .. a:args .. ' 2>&1'
  let out = system(cmd)
  return [out, v:shell_error]
endfunc

func! s:RunHelp() abort
  let out = system(v:progpath .. ' --help 2>&1')
  return out
endfunc

func! s:path_join(dir, file) abort
  if a:dir =~ '[\\/]$'
    return a:dir .. a:file
  endif
  return a:dir .. '/' .. a:file
endfunc

func! s:HasStartuptime() abort
  let help = s:RunHelp()
  return help =~# '\<--startuptime\>'
endfunc

func! s:HasLog() abort
  if !has('channel')
    return 0
  endif
  let help = s:RunHelp()
  return help =~# '\<--log\>'
endfunc

func! s:AssertNoCrash(out, code, ctx) abort
  if a:out =~? 'Segmentation fault\|core dumped\|caught deadly signal\|Vim: Signal'
    echoerr a:ctx .. ': unexpected crash: ' .. a:out
    cquit 1
  endif
endfunc

" 1) --startuptime with non-existent directory should not crash
if s:HasStartuptime()
  let basedir = fnamemodify(tempname(), ':p') .. '_no_such_dir'
  let badst = s:path_join(basedir, 'Xstartuptime')
  let [out1, code1] = s:RunVim('--startuptime ' .. shellescape(badst) .. ' -c qa!')
  call s:AssertNoCrash(out1, code1, '--startuptime to non-existent dir')
endif

" 2) --startuptime to a valid file should create the file and write something
if s:HasStartuptime()
  let goodst = tempname()
  call delete(goodst)
  let [out2, code2] = s:RunVim('--startuptime ' .. shellescape(goodst) .. ' -c qa!')
  if !filereadable(goodst)
    echoerr '--startuptime to valid file: file was not created'
    cquit 1
  endif
  let stlines = readfile(goodst)
  if empty(stlines)
    echoerr '--startuptime to valid file: file is empty'
    cquit 1
  endif
  call delete(goodst)
endif

" 3) --log with non-existent directory should not crash
if s:HasLog()
  let basedir2 = fnamemodify(tempname(), ':p') .. '_no_such_dir2'
  let badlog = s:path_join(basedir2, 'Xlogfile')
  let [out3, code3] = s:RunVim('--log ' .. shellescape(badlog) .. ' -c qa!')
  call s:AssertNoCrash(out3, code3, '--log to non-existent dir')
endif

" 4) --log to a valid file should create the file and write something
if s:HasLog()
  let goodlog = tempname()
  call delete(goodlog)
  let [out4, code4] = s:RunVim('--log ' .. shellescape(goodlog) .. ' -c qa!')
  if !filereadable(goodlog)
    echoerr '--log to valid file: log file was not created'
    cquit 1
  endif
  let lines = readfile(goodlog)
  if empty(lines)
    echoerr '--log to valid file: log file is empty'
    cquit 1
  endif
  call delete(goodlog)
endif

qall!
