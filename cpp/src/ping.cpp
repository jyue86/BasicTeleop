#include <holoscan/holoscan.hpp>
#include <holoscan/operators/ping_tx/ping_tx.hpp>
#include <holoscan/operators/ping_rx/ping_rx.hpp>

class MyPingApp : public holoscan::Application {
 public:
  void compose() override {
    using namespace holoscan;
    // Create the tx and rx operators
    auto tx = make_operator<ops::PingTxOp>("tx", make_condition<CountCondition>(10));
    auto rx = make_operator<ops::PingRxOp>("rx");

    // Connect the operators into the workflow: tx -> rx
    add_flow(tx, rx);
  }
};

int main(int argc, char** argv) {
  auto app = holoscan::make_application<MyPingApp>();
  app->run();

  return 0;
}