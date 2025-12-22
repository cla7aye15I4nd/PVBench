let caught = 'no'
try
  exe repeat('0', 987) .. "0\xdd\x80\xdd\x80\xdd\x80\xdd\x80"
catch /E492:/
  let caught = 'yes'
endtry
qall!