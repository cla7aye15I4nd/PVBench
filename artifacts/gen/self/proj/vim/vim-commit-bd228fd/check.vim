func Test_help_long_argument()
  try
    exe 'help \%' .. repeat('0', 1021)
  catch
    call assert_match("E149:", v:exception)
  endtry
endfunc


