#include "testUtils.h"
#include "schedulerQueue.h"
#include <stdlib.h>

//create setup, tearDown, fixtureSetup, fixtureTearDown methods if needed
schedulerQueue *queue;
void tearDown(){
	dispose(queue);
}
void test_create_process(){
	schedulerQueue expected = {NULL,0};
	queue = create();
	ASSERT(queue->head == expected.head);
	ASSERT(queue->length == expected.length);
}

void test_add_first_process(){
	schedulerQueue expected = {NULL,0};
	Status statusp1 = {0,1,0};
	Process p1 = {"p1",1000,statusp1,3,NULL};
	queue = create();
	ASSERT(1 == insertProcess(queue, &p1));
	ASSERT(queue->head == &p1);
	ASSERT(queue->head->next == NULL);
}
void test_add_process_with_priority_higher_than_first_process(){
	schedulerQueue expected = {NULL,0};
	Status statusp1 = {0,1,0};
	Process p1 = {"p1",1000,statusp1,3,NULL};
	Process p2 = {"p2",500,statusp1,1,NULL};
	queue = create();
	ASSERT(1 == insertProcess(queue, &p1));
	ASSERT(2 == insertProcess(queue, &p2));
	ASSERT(queue->head == &p2);
	ASSERT(queue->head->next == &p1);
}
void test_add_process_with_priority_somewhere_in_between_process_queue(){
	schedulerQueue expected = {NULL,0};
	Status statusp1 = {0,1,0};
	Process *second,*third;
	Process p1 = {"p1",1000,statusp1,3,NULL};
	Process p2 = {"p2",500,statusp1,1,NULL};
	Process p3 = {"p3",400,statusp1,2,NULL};
	queue = create();
	ASSERT(1 == insertProcess(queue, &p1));
	ASSERT(2 == insertProcess(queue, &p2));
	ASSERT(3 == insertProcess(queue, &p3));
	ASSERT(queue->head == &p2);
	second = queue->head->next;
	third = second->next;
	ASSERT(second == &p3);
	ASSERT(third == &p1);
	ASSERT(third->next == NULL);
}
