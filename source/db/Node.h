#ifndef SPDB_NODE_H_
#define SPDB_NODE_H_
#include "../utility/TypeTraits.h"
#include "Cursor.h"
#include "DataBlock.h"
#include "XPath.h"
#include <array>
#include <complex>
#include <functional>
#include <map>
#include <memory>
#include <string>
#include <variant>
#include <vector>
namespace sp::db
{
class Node;
class NodeBackend;
class NodeObject;
class NodeArray;
class DataBlock;

} // namespace sp::db

M_REGISITER_TYPE_TAG(Block, sp::db::DataBlock);
M_REGISITER_TYPE_TAG(Path, sp::db::Path);

M_REGISITER_TYPE_TAG(Object, std::shared_ptr<sp::db::NodeObject>);
M_REGISITER_TYPE_TAG(Array, std::shared_ptr<sp::db::NodeArray>);

namespace sp::db
{
typedef std::variant<std::nullptr_t,
                     std::shared_ptr<NodeObject>,        //Object
                     std::shared_ptr<NodeArray>,         //Array
                     DataBlock,                          //Block
                     Path,                               //Path
                     bool,                               //Boolean,
                     int,                                //Integer,
                     long,                               //Long,
                     float,                              //Float,
                     double,                             //Double,
                     std::string,                        //String,
                     std::array<int, 3>,                 //IntVec3,
                     std::array<long, 3>,                //LongVec3,
                     std::array<float, 3>,               //FloatVec3,
                     std::array<double, 3>,              //DoubleVec3,
                     std::complex<double>,               //Complex,
                     std::array<std::complex<double>, 3> //ComplexVec3,
                     >
    node_value_type;

class NodeObject : public std::enable_shared_from_this<NodeObject>
{

public:
    NodeObject();

    virtual ~NodeObject() = default;

    NodeObject(const NodeObject&) = delete;

    NodeObject(NodeObject&&) = delete;

    // template <typename... Args>
    // NodeObject(Args&&... args) {}

    static std::shared_ptr<NodeObject> create(const NodeObject& opt);

    virtual std::shared_ptr<NodeObject> copy() const = 0;

    virtual void load(const NodeObject&);

    virtual void save(const NodeObject&) const;

    virtual bool is_same(const NodeObject&) const;

    virtual bool is_valid() const;

    virtual bool empty() const;

    virtual size_t size() const;

    virtual void clear();

    virtual void reset();

    virtual Cursor<Node> children();

    virtual Cursor<const Node> children() const;

    virtual void for_each(std::function<void(const std::string&, const Node&)> const&) const;

    //----------------

    virtual void update(const Path&, const Node&, const NodeObject& opt = {});

    virtual Node merge(const Path&, const Node& patch, const NodeObject& opt = {});

    virtual Node fetch(const Path&, const Node& projection, const NodeObject& opt = {}) const;

    //----------------

    virtual bool contain(const std::string& name) const;

    virtual void update_value(const std::string& name, Node&& v);

    virtual Node insert_value(const std::string& name, Node&& v);

    virtual Node find_value(const std::string& name) const;
};

class NodeArray : public std::enable_shared_from_this<NodeArray>
{
    std::shared_ptr<std::vector<Node>> m_container_;

public:
    NodeArray()
        : m_container_(std::make_shared<std::vector<Node>>()) {}

    ~NodeArray() = default;

    template <typename IT>
    NodeArray(const IT& ib, const IT& ie)
        : m_container_(std::make_shared<std::vector<Node>>(ib, ie)) {}

    NodeArray(const NodeArray& other);

    NodeArray(NodeArray&& other);

    void swap(NodeArray& other);

    NodeArray& operator=(const NodeArray& other);

    void clear();

    size_t size() const;

    Cursor<Node> children();

    Cursor<const Node> children() const;

    void for_each(std::function<void(int, Node&)> const&);

    void for_each(std::function<void(int, const Node&)> const&) const;

    Node slice(int start, int stop, int step);

    Node slice(int start, int stop, int step) const;

    void resize(std::size_t num);

    Node& insert(int idx, Node);

    Node& update(int idx, Node);

    Node& at(int idx);

    const Node& at(int idx) const;

    Node& push_back(Node v);

    Node pop_back();
};

class Node
{
public:
    typedef node_value_type value_type;

    typedef traits::type_tags<value_type> tags;

    Node() = default;

    ~Node() = default;

    template <typename... Args,
              std::enable_if_t<std::is_constructible<value_type, Args...>::value, int> = 0>
    Node(Args&&... args);

    Node(char const* c);

    Node(std::initializer_list<Node> init);

    Node(Node& other);

    Node(const Node& other);

    Node(Node&& other);

    void swap(Node& other);

    size_t type() const;

    void clear();

    NodeArray& as_array();

    const NodeArray& as_array() const;

    NodeObject& as_object();

    const NodeObject& as_object() const;

    void set_value(value_type v) { m_value_.swap(v); }

    value_type& get_value() { return m_value_; }

    const value_type& get_value() const { return m_value_; }

    template <typename V, typename First, typename... Others>
    void as(First&& first, Others&&... others) { m_value_.emplace<V>(std::forward<First>(first), std::forward<Others>(others)...); }

    template <int IDX, typename First, typename... Others>
    void as(First&& first, Others&&... others) { m_value_.emplace<IDX>(std::forward<First>(first), std::forward<Others>(others)...); }

    template <typename V>
    V as() const { return traits::convert<V>(m_value_); }

    template <int IDX>
    decltype(auto) as() const { return std::get<IDX>(m_value_); }

    template <int IDX>
    decltype(auto) as() { return std::get<IDX>(m_value_); }

private:
    value_type m_value_;
}; // namespace sp::db

template <typename... Args,
          std::enable_if_t<std::is_constructible<Node::value_type, Args...>::value, int>>
Node::Node(Args&&... args) : m_value_(std::forward<Args>(args)...) {}

std::ostream& operator<<(std::ostream& os, Node const& node);
std::ostream& operator<<(std::ostream& os, NodeObject const& node);
std::ostream& operator<<(std::ostream& os, NodeArray const& node);

namespace literals
{
using namespace std::complex_literals;
using namespace std::string_literals;
} // namespace literals
} // namespace sp::db

#endif //SP_NODE_H_