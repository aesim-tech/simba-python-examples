#ifndef SIMBA_EXPORT

	#ifdef __cplusplus
	#define EXTERN_C extern "C" 
	#else
	#define EXTERN_C
	#endif

	#if defined(_MSC_VER) || defined(_WIN64)
		#if defined(SIMBA_EXTERNAL_LIB_EXPORT)
			#define SIMBA_EXPORT EXTERN_C __declspec( dllexport )
		#else
			#define SIMBA_EXPORT EXTERN_C __declspec( dllimport )
		#endif
	#elif defined(__GNUC__)
		#if defined(SIMBA_EXTERNAL_LIB_EXPORT)
			#define SIMBA_EXPORT EXTERN_C __attribute__((visibility("default")))
		#else
			#define SIMBA_EXPORT EXTERN_C
		#endif
	#else 
		#define SIMBA_EXPORT EXTERN_C __declspec( dllexport )
		#pragma warning Unknown dynamic link import/export semantics.
	#endif
#endif

typedef enum {
	SNAPSHOT_CREATE = 1,
	SNAPSHOT_UPDATE = 2,
	SNAPSHOT_LOAD = 3,
	SNAPSHOT_DELETE = 4,
} snapshot_mode;

SIMBA_EXPORT void initialize();
SIMBA_EXPORT void calculate_outputs(double* outputs, double* inputs, double time, double time_step);
SIMBA_EXPORT void terminate();
SIMBA_EXPORT void* snapshot(snapshot_mode mode, void* snapshot);