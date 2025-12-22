set virtualedit=all
args Xa Xb
all
call setline(1, ['', '', ''])
call cursor(3, 1)
wincmd w
call setline(1, 'foobar')
normal! $lv0
all
call setreg('"', 'baz')
normal! [P
set virtualedit=
bw! Xa Xb
qall!