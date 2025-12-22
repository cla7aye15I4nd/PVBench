struct foo {
};

struct bar {
    friend bool operator==(const bar& a, const bar& b);
    friend class foo;
};

bool operator==(const bar& a, const bar& b) = default;