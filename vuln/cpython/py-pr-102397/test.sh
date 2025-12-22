#!/bin/bash -eu
patch -p1 <<EOF
diff --git a/Lib/asyncio/base_events.py b/Lib/asyncio/base_events.py
index 6e6e5aaac15..85018797db3 100644
--- a/Lib/asyncio/base_events.py
+++ b/Lib/asyncio/base_events.py
@@ -1593,7 +1593,9 @@ async def create_server(
                     if reuse_address:
                         sock.setsockopt(
                             socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
-                    if reuse_port:
+                    # Since Linux 6.12.9, SO_REUSEPORT is not allowed
+                    # on other address families than AF_INET/AF_INET6.
+                    if reuse_port and af in (socket.AF_INET, socket.AF_INET6):
                         _set_reuseport(sock)
                     if keep_alive:
                         sock.setsockopt(
diff --git a/Lib/socket.py b/Lib/socket.py
index be37c24d617..727b0e75f03 100644
--- a/Lib/socket.py
+++ b/Lib/socket.py
@@ -937,7 +937,9 @@ def create_server(address, *, family=AF_INET, backlog=None, reuse_port=False,
                 # Fail later on bind(), for platforms which may not
                 # support this option.
                 pass
-        if reuse_port:
+        # Since Linux 6.12.9, SO_REUSEPORT is not allowed
+        # on other address families than AF_INET/AF_INET6.
+        if reuse_port and family in (AF_INET, AF_INET6):
             sock.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
         if has_ipv6 and family == AF_INET6:
             if dualstack_ipv6:
diff --git a/Lib/socketserver.py b/Lib/socketserver.py
index cd028ef1c63..35b2723de3b 100644
--- a/Lib/socketserver.py
+++ b/Lib/socketserver.py
@@ -468,7 +468,12 @@ def server_bind(self):
         """
         if self.allow_reuse_address and hasattr(socket, "SO_REUSEADDR"):
             self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
-        if self.allow_reuse_port and hasattr(socket, "SO_REUSEPORT"):
+        # Since Linux 6.12.9, SO_REUSEPORT is not allowed
+        # on other address families than AF_INET/AF_INET6.
+        if (
+            self.allow_reuse_port and hasattr(socket, "SO_REUSEPORT")
+            and self.address_family in (socket.AF_INET, socket.AF_INET6)
+        ):
             self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
         self.socket.bind(self.server_address)
         self.server_address = self.socket.getsockname()
EOF
./configure --without-pymalloc --with-pydebug
make -j$(nproc)
make test TESTOPTS="-x test_email" -j$(nproc)
