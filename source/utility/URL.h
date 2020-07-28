#ifndef SP_URL_H_
#define SP_URL_H_
#include <string>
#include <tuple>
#include <variant>
namespace sp
{
std::string urljoin(std::string const& base, std::string const& path);

std::tuple<std::string /*scheme */,
           std::string /*authority */,
           std::string /*path*/,
           std::string /*query*/,
           std::string /*fragment */>
urlparser(std::string const& url);

/*
     @ref: https://www.ietf.org/rfc/rfc3986.txt

*/
class URI
{
public:
    typedef std::variant<std::string /* key or query*/, int /* index */, std ::tuple<int, int, int> /* slice */> segment_type;

    enum segment_type
    {
        KEY,
        INDEX,
        SLICE
    };

    typedef URI this_type;
    URI(const std::string&);
    URI(const URI&);
    URI(URI&&);
    ~URI();

    template <typename FirstSegment, typename... Others>
    URI(const URI& other, FirstSegment&& seg, Others&&... others) : URI(other) { append(std::forward<FirstSegment>(seg), std::forward<Others>(others)...); }

    template <typename FirstSegment, typename... Others>
    URI(URI&& other, FirstSegment&& seg, Others&&... others) : URI(std::forward<URI>(other)) { append(std::forward<FirstSegment>(seg), std::forward<Others>(others)...); }

    void swap(this_type& other)
    {
        std::swap(m_scheme_, other.m_scheme_);
        std::swap(m_authority_, other.m_authority_);
        std::swap(m_path_, other.m_path_);
        std::swap(m_query_, other.m_query_);
        std::swap(m_fragment_, other.m_fragment_);
    }

    this_type& operator=(const this_type& other)
    {
        this_type(other).swap(*this);
        return *this;
    }

    std::string str();

    const std::string& scheme() const { return m_scheme_; }
    void scheme(const std::string& s) { m_scheme_ = s; }

    const std::string& authority() const { return m_authority_; }
    void authority(const std::string& s) { m_authority_ = s; }

    const std::string& query() const { return m_query_; }
    void query(const std::string& s) { m_query_ = s; }

    const std::string& fragment() const { return m_fragment_; }
    void fragment(const std::string& s) { m_fragment_ = s; }

    void append(const std::string& path);
    void append(int idx);
    void append(int b, int e, int seq = 1);

    template <typename Key>
    this_type operator[](const Key& key) const { return URI(*this, key); }

    this_type operator/(const std::string& key) const { return URI(*this, key); }

    size_t size() const { return m_path_.size(); }

    const auto& begin() const { return m_path_.begin(); }

    const auto& end() const { return m_path_.end(); }

private:
    std::string m_scheme_;
    std::string m_authority_;
    std::vector<segment_type> m_path_;
    std::string m_query_;
    std::string m_fragment_;
};

} // namespace sp
#endif //SP_URL_H_