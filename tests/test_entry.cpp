#include "db/Entry.h"
#include "db/XPath.h"
#include "utility/Logger.h"
#include <iostream>

#define CATCH_CONFIG_MAIN
#include "catch/catch.hpp"

using namespace sp::db::literals;

TEST_CASE("Object", "[SpDB:Entry]")
{
    sp::db::Entry entry({{"B"s, {{"b", 1}, {"c", "hello world"}}}});

    VERBOSE << entry;

    REQUIRE(entry["B"]["b"].as<int>() == 1);

    REQUIRE(entry["B"]["c"].as<std::string>() == "hello world");

    entry["A"s].as<std::string>("1234");
    entry["B"s].as<std::string>("5678");

    REQUIRE(entry.type() == sp::db::Node::tags::Object);

    REQUIRE(entry.count() == 2);
}

TEST_CASE("Path", "[SpDB:Array]")
{
    sp::db::Entry entry;

    std::string message = "hello world!";

    entry["D/E/F"_p] = message;

    REQUIRE(entry["D"]["E"]["F"].as<std::string>() == message);

    VERBOSE << entry;
}

TEST_CASE("Array", "[SpDB:Entry]")
{
    sp::db::Entry entry;

    entry["C"].resize(4);

    REQUIRE(entry["C"].count() == 4);
    REQUIRE(entry["C"].type() == sp::db::Node::tags::Array);

    entry["C"][2] = 12344.56;
    entry["C"][3] = 6.0 + 4.0i;

    entry["C"].push_back().as<int>(135);
    entry["C"].push_back().as<float>(6.0);
    entry["C"].push_back().as<std::string>("3.1415926");

    REQUIRE(entry["C"].count() == 7);

    REQUIRE(entry["C"][2].as<double>() == 12344.56);
    REQUIRE(entry["C"][4].as<std::string>() == "135");
    REQUIRE(entry["C"][6].as<double>() == 3.1415926);

    VERBOSE << entry;
}
