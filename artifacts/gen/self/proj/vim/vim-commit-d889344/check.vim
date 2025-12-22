" this was going over the end of IObuff
func Test_report_error_with_composing()
  let caught = 'no'
  try
    exe repeat('0', 987) .. "0\xdd\x80\xdd\x80\xdd\x80\xdd\x80"
  catch /E492:/
    let caught = 'yes'
  endtry
  call assert_equal('yes', caught)
endfunc

