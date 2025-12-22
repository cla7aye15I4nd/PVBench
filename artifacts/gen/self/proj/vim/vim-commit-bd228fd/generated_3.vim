" Test for help argument handling overflow fix (patch 3669)
" Runs in Ex mode (-e -s). Ensures no crash and only benign errors (E149).

set nocp

" Helper: run :help on a topic, allow only E149 errors (no help found).
func s:TryHelp(topic, label)
  try
    exe 'silent help ' . a:topic
  catch
    if v:exception !~# 'E149:'
      echoerr 'Unexpected error for ' . a:label . ': ' . v:exception
      cquit 1
    endif
  endtry
endfunc

" 1) Original PoC: very long \%... argument (previously could overflow)
call s:TryHelp('\%' . repeat('0', 1021), 'long-%-1021')

" 2) Even longer to exceed IOSIZE by a good margin
call s:TryHelp('\%' . repeat('0', 2048), 'long-%-2048')

" 3) Edge case from code path: handle /\\_$ -> should become /\\_\$ internally
call s:TryHelp('\_$', 'underscore-dollar-short')
call s:TryHelp('\_$' . repeat('X', 2000), 'underscore-dollar-long')

" 4) Test other accepted starters in the set [% _ z @] with long tails
for ch in ['%', '_', 'z', '@']
  call s:TryHelp('\' . ch . repeat('A', 1500), 'starter-' . ch . '-1500')
endfor

" 5) Boundary-adjacent lengths around typical IOSIZE (approx 1024)
for L in [1000, 1023, 1024, 1100]
  call s:TryHelp('\%' . repeat('b', L), 'boundary-%-' . string(L))
endfor

qall!
