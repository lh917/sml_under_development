import double_integrator_controller as dic
import double_integrator_neutral_controller as dinc
import double_integrator_bounded_and_component_wise_controller as dibacwc
import double_integrator_bounded_not_component_wise_controller as dibncwc

di_ctrl_dictionary = {
"DoubleIntegratorController": dic.DoubleIntegratorController,
"DoubleIntegratorDefaultController": dinc.DoubleIntegratorNeutralController,
"DoubleIntegratorNeutralController": dinc.DoubleIntegratorNeutralController,
"DoubleIntegratorBoundedAndComponentWiseController": dibacwc.DoubleIntegratorBoundedAndComponentWiseController,
"DoubleIntegratorBoundedNotComponentWiseController": dibncwc.DoubleIntegratorBoundedNotComponentWiseController
}
