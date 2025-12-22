" Test for heap buffer overflow in tag jumping with nostartofline (#16796)
" The vulnerability was that cursor column was not reset when jumping to tag,
" causing access to invalid column position.
func Test_tag_excmd_with_nostartofline()
  call writefile(["!_TAG_FILE_ENCODING\tutf-8\t//",
        \ "f\tXfile\tascii"],
        \ 'Xtags', 'D')
  call writefile(['f', 'foobar'], 'Xfile', 'D')

  set nostartofline
  new Xfile
  setlocal tags=Xtags
  normal! G$
  " This used to cause heap-buffer-overflow
  tag f
  " If we reach here without crash, the fix is working
  call assert_true(1)

  bwipe!
  set startofline&
endfunc
