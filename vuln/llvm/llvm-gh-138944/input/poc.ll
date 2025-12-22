target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-gnu"

define <4 x float> @_Z3foo4fVec(<4 x float> %vIn.coerce) "target-features"="+fma" {
entry:
  %fneg.i = fneg <4 x float> %vIn.coerce
  %0 = tail call <4 x float> @llvm.x86.sse.rcp.ps(<4 x float> %fneg.i)
  %1 = fcmp une <4 x float> zeroinitializer, %vIn.coerce
  %.neg.i = select <4 x i1> %1, <4 x float> %0, <4 x float> splat (float 1.000000e+00)
  %factor.i = fmul contract <4 x float> %0, zeroinitializer
  %sub.i = fadd nsz contract <4 x float> %.neg.i, %factor.i
  ret <4 x float> %sub.i
}
