let save_columns = &columns
set columns=5000
set noswapfile
let dirname = getcwd() . "/Xdir"
let longdirname = dirname . repeat('/' . repeat('d', 255), 4)
let longfilename = longdirname . '/' . repeat('a', 255)
call mkdir(longdirname, 'p')
call writefile(['Totum', 'Table'], longfilename)
new
exe "next Xfile " . longfilename
exe "normal iT\<C-N>"

bwipe!
exe 'bwipe! ' . longfilename
call delete(dirname, 'rf')
let &columns = save_columns
set swapfile&
qall!