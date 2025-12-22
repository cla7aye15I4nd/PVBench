template < template < typename> typename> struct TypeTList;
template < typename >
constexpr auto LambdaThing = []< template < typename> typename... Args >( TypeTList< Args... > ) {};
template < template < typename > typename TheThingT, typename TheParam >
struct TraitApplier {
    template < typename >
    using X = TheThingT< TheParam >;
};
template < typename Traits >
concept FooTraitsConcept = requires {
    LambdaThing< typename Traits::FooTypes >;
};
template < FooTraitsConcept >
class Foo;
struct FooTraits {
    using FooTypes = int;
};
void foo() {
    TraitApplier< Foo, FooTraits> x;
}
