from holoscan.conditions import CountCondition
from holoscan.core import Application, Operator, OperatorSpec
from holoscan.operators import PingRxOp, PingTxOp

class PingMxOp(Operator):
    """Example of an operator modifying data.

This operator has 1 input and 1 output port:
input:  "in"
output: "out"

The data from the input is multiplied by the "multiplier" parameter

"""

    def setup(self, spec: OperatorSpec):
        spec.input("in")
        spec.output("out")
        spec.param("multiplier", 2)

    def compute(self, op_input, op_output, context):
        value = op_input.receive("in")
        print(f"Middle message value:{value}")

        # Multiply the values by the multiplier parameter
        value *= self.multiplier

        op_output.emit(value, "out")

class MyPingApp(Application):
    def compose(self):
        # Define the tx, mx, rx operators, allowing the tx operator to execute 10 times
        tx = PingTxOp(self, CountCondition(self, 10), name="tx")
        mx = PingMxOp(self, name="mx", multiplier=3)
        rx = PingRxOp(self, name="rx")

        # Define the workflow: tx -> mx -> rx
        self.add_flow(tx, mx)
        self.add_flow(mx, rx)


def main():
    app = MyPingApp()
    app.run()


if __name__ == "__main__":
    main()