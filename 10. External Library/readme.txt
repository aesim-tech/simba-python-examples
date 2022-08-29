Example of SIMBA design using the External Library model. 

- Library Built as x64 DLL on windows
- Example of build command with gcc x86_64 : 
	- x86_64-w64-mingw32-gcc.exe -D SIMBA_EXTERNAL_LIB_EXPORT -c library.c -O3
	- x86_64-w64-mingw32-gcc.exe -shared -o library.dll library.o
- The libray must export the functions defined in simba_library.h
