void testFailed(const char* fileName, int lineNumber, char* expression);
#define ASSERT(expr) 	if(!(expr)) testFailed(__FILE__,__LINE__,#expr)
