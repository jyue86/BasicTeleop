#include <holoscan/holoscan.hpp>
#include <holoscan/operators/ping_rx/ping_rx.hpp>
#include <holoscan/operators/ping_tx/ping_tx.hpp>

namespace holoscan {
    class RemoteStationFragment : public Fragment {
        public:
        void compose() override {
        
            // Define operators here
            // auto operator1 = make_operator<ops::Operator1>("operator1", ...);
            // auto operator2 = make_operator<ops::Operator2>("operator2", ...);
        
            // Add operators to the fragment
            // add_operator(operator1);
            // add_operator(operator2);
        
            // Define data flows between operators
            // add_flow(operator1, operator2);
            auto tx = make_operator<ops::PingTxOp>("tx", make_condition<CountCondition>(100));
            add_operator(tx);
        }
    };

    class VehicleFragment: public Fragment {
        public:
        void compose() override {
            auto rx = make_operator<ops::PingRxOp>("rx");
            add_operator(rx);
        }
    };

    class DistributedApp: public Application {
    public:
        void compose() override {
            // Create fragments
            auto remote_station_fragment = make_fragment<RemoteStationFragment>("remote_station_fragment");
            auto vehicle_fragment = make_fragment<VehicleFragment>("vehicle_fragment");

            // Add fragments to the application
            add_fragment(remote_station_fragment);
            add_fragment(vehicle_fragment);
            add_flow(remote_station_fragment, vehicle_fragment, {{"tx.out", "rx.in"}});
        }
    };
};

int main() {
    auto app = holoscan::make_application<holoscan::DistributedApp>();
    app->run();

    return 0;
}