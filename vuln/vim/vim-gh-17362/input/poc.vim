let lines =<< trim END
    imp(",G0}11*f[+\x","#|
END
new
call setline(1, lines)
source
qall!
