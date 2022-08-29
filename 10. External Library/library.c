#include "simba_library.h" 
#include <stdlib.h>


typedef struct{
    double duty_cycle;
    double Verror;
    double Verror_prev;
    double Isp;
    double Ierror;
    double Ierror_prev;
    double Vsw;
} model_data;

model_data data; 

void initialize() {
	data.duty_cycle = 0;
	data.Verror_prev = 0;
	data.Isp = 0;
	data.Ierror_prev = 0;
	data.Vsw = 0;
}

void calculate_outputs(double* outputs, double* inputs, double time, double time_step) {

	const double clock = inputs[0];
	if(clock == 1) // Clock
	{
		double V_measured = inputs[1];
		double I_measured = inputs[2];
		double V_REF = 5;

		// Voltage loop
		double Verror = V_REF - V_measured;
		data.Isp = data.Isp + 0.4894*(Verror - data.Verror_prev) + 0.0174*Verror; 		
		data.Verror_prev = Verror;
		if(data.Isp > 20)data.Isp = 20;
		if(data.Isp < -20)data.Isp = -20;

		// Current loop
		double Ierror = data.Isp - I_measured;
		data.Vsw = data.Vsw + 3.0588*(Ierror - data.Ierror_prev) + 0.2251*Ierror;		
		data.Ierror_prev = Ierror;
		if(data.Vsw > 10)data.Vsw = 10;
		if(data.Vsw < 0)data.Vsw = 0;

		
		// Duty-Cycle
		data.duty_cycle = data.Vsw*300/10; 
	}
	
	outputs[0] = data.duty_cycle;
}

void terminate() {
}

/*
 * Function: snapshot (DO NOT MODIFY)
 */
void* snapshot(snapshot_mode mode, void* snapshot_ptr) {
	model_data* model_data_ptr;
	switch (mode) {
		case SNAPSHOT_CREATE: // Create and return a snapshot of the current model state
			model_data_ptr = (model_data*)malloc(sizeof(model_data));
			if (model_data_ptr == 0) return 0;
			*model_data_ptr = data;
			return (void*)model_data_ptr;

		case SNAPSHOT_UPDATE:  // Update an existing snapshot with current model data
			model_data_ptr = (model_data*)snapshot_ptr;
			*model_data_ptr = data;
			return snapshot_ptr;

		case SNAPSHOT_LOAD:  // Restore model data 
			model_data_ptr = (model_data*)snapshot_ptr;
			data = *model_data_ptr;
			return snapshot_ptr;

		case SNAPSHOT_DELETE: // Free the resources allocated in SNAPSHOT_CREATE
			free(snapshot_ptr);
			return 0;
	}
}