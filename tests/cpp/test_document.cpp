#include "Entry.h"
#include "Node.h"
#include <iostream>

#define CATCH_CONFIG_MAIN
#include "catch.hpp"

TEST_CASE("SpDocument Create", "[SpDB]")
{
    sp::Node node;

    // node.set_attribute("A", "a");
    // // node.set_attribute("B", "1234");
    // node["A"].set_value<std::string>("1234");
    // node["B"].set_value<std::string>("1234");
    node.push_back().set_value<std::string>("1234");
    // std::cout << node << std::endl;
    // std::cout << "====================================" << std::endl;
    // node.as_table()["C"].as_array().push_back().as_scalar().set_value<std::string>("1234");

    // // node.set_value<std::string>("1234");
    // std::cout << node << std::endl;

    // // std::cout << "====================================" << std::endl;

    // // node.append().set_value<std::string>("4567");
    // std::cout << "====================================" << std::endl;

    // node.as_array().push_back().as_scalar().set_value<std::string>("7890");

    // std::cout << node << std::endl;

    // REQUIRE(node.child("C").child(0).get_value<std::string>() == "1234");
}