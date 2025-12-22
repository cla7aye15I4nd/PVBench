var ab = new ArrayBuffer(100);
var ta = new Uint8Array(ab, 0, 20);
ta.constructor = {
  [Symbol.species]: function (len) {
    return new Uint8Array(ab, 1, len);
  },
};

var tb = ta.slice();