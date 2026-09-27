# Have a myfile.c source file and myfileTest.c test file
# execute the tests using 
# ./runTest.sh mymath.c
#
# Instructions for tests
# include testUtils.h for the ASSERT function
# test methods should have signature of void test_yourtest()
# Edited Oct 26, 2013.
# Treats multiple asserts in one test as a single test
# prints the failed expression also.
# More accurate in locating crashes in setup and teardown
source=$1
testSource=`echo $source |sed -e s/.c$/Test.c/`
testRunnerSource=`echo $source |sed -e s/.c$/TestRunner.c/`
testRunnerExe=`echo $source |sed -e s/.c$/TestRunner.exe/`
rm -f $testRunnerExe
cat > $testRunnerSource<<END_OF_TESTRUNNERSOURCE
#include <stdio.h>

int testCount=-1;
int passCount=0;
void setup();
void tearDown();

void fixtureSetup();
void fixtureTearDown();
void incrementTestCount();
void incrementPassCount();
int currentTestFailed=0;

void testStarted(char* name){
	incrementTestCount();
	currentTestFailed=0;
	printf("\t%s\n",name);
}

void testEnded(){
	if(!currentTestFailed)
		incrementPassCount();
}

void resetTestCount(){
	testCount=0;
	passCount=0;
	printf("********* Starting tests\n\n");
}

void summarizeTestCount(){
	printf("\n********* Ran %d tests passed %d failed %d\n",testCount,passCount,testCount-passCount);
}

void incrementTestCount(){
	testCount++;
}

void incrementPassCount(){
	passCount++;
}

void testFailed(const char* fileName, int lineNumber, char* expression){
	currentTestFailed = 1;
	printf("\t\t %s : failed at %s:%d\n",expression, fileName,lineNumber);
}

END_OF_TESTRUNNERSOURCE
cat $testSource| awk 'BEGIN {
	print "int main(){"
	print "	fixtureSetup();"
	print "	resetTestCount();"
	print ""
}
/^void setup()/ { hasSetup=1}
/^void tearDown()/ { hastearDown=1}
/^void fixtureSetup()/ { hasfixtureSetup=1}
/^void fixtureTearDown()/ { hasfixtureTearDown=1}
/^void test_/ {
	split($2,parts,"(")
	print "	testStarted(\"" parts[1] "\");"
	print "	setup();"	
	print "		"parts[1]"();"
	print "	tearDown();"
	print "	testEnded();"
}
END {
	print ""
	print "	summarizeTestCount();"
	print "	fixtureTearDown();"
	print "	return 0;"
	print "}"
	if(hasSetup!=1){
		print ""
		print "void setup(){}"
	}
	if(hastearDown!=1){
		print ""
		print "void tearDown(){}"
	}
	if(hasfixtureSetup!=1){
		print ""
		print "void fixtureSetup(){}"
	}
	if(hasfixtureTearDown!=1){
		print ""
		print "void fixtureTearDown(){}"
	}
}' >> $testRunnerSource

external_libs=`for arg in $*; do
	echo $arg | awk '
	$1 ~/-need:/ {
		split($1,parts,":"); 
		printf " " parts[2]
	}'
done`
compile_testRunner="gcc -g -o $testRunnerExe $testRunnerSource $testSource $source $external_libs"
$compile_testRunner
$testRunnerExe
