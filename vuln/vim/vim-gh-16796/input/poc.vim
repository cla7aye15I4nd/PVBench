call writefile(["!_TAG_FILE_ENCODING\tutf-8\t//",
      \ "f\tXfile\tascii"],
      \ 'Xtags')
call writefile(['f', 'foobar'], 'Xfile')
set nostartofline
new Xfile
setlocal tags=Xtags
normal! G$
tag f
qall!