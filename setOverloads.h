#pragma once
#include <algorithm>
#include <iterator>
#include <unordered_set>

template <class T>
std::unordered_set<T>
operator-(const std::unordered_set<T> &base, const std::unordered_set<T> &other)
{
    std::unordered_set<T> result;
    result = base;
    for (auto &elem : other)
        result.erase(elem);
    return result;
}

template <class T>
std::unordered_set<T>
operator&(const std::unordered_set<T> &base, const std::unordered_set<T> &other)
{
    if (base.size() < other.size()) {
        return other & base;
    }

    std::unordered_set<T> result;
    auto e = other.end();
    for (auto &v : base) {
        if (other.find(v) != e) {
            result.insert(v);
        }
    }
    return result;
}

template <class T>
std::unordered_set<T>
operator+(const std::unordered_set<T> &base, const std::unordered_set<T> &other)
{
    std::unordered_set<T> result;
    // result.insert(base.begin(), base.end());
    result = base;
    result.insert(other.begin(), other.end());
    return result;
}

template <class T>
std::unordered_set<T>
operator|(const std::unordered_set<T> &base, const std::unordered_set<T> &other)
{
    return base + other;
}

/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

template <class T>
std::vector<T>
operator-(const std::vector<T> &base, const std::vector<T> &other)
{
    std::vector<T> result;
    std::set_difference(
        base.begin(), base.end(), other.begin(), other.end(),
        std::inserter(result, result.end())
    );
    return result;
}

template <class T>
std::vector<T>
operator&(const std::vector<T> &base, const std::vector<T> &other)
{
    std::vector<T> result;
    std::set_intersection(
        base.begin(), base.end(), other.begin(), other.end(),
        std::inserter(result, result.end())
    );
    return result;
}

template <class T>
std::vector<T>
operator|(const std::vector<T> &base, const std::vector<T> &other)
{
    return base + other;
}

template <class T>
std::vector<T>
operator+(const std::vector<T> &base, const std::vector<T> &other)
{
    std::vector<T> result;
    std::set_union(
        base.begin(), base.end(), other.begin(), other.end(),
        std::back_inserter(result)
    );
    return result;
}
