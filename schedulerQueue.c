#include "schedulerQueue.h"
#include <stdlib.h>
schedulerQueue* create(){
	schedulerQueue *queue = calloc(sizeof(schedulerQueue),1);
	return queue;
}
int insertAtStart(schedulerQueue *queue, Process *process){
	if(queue->head == NULL)
			process->next = NULL;
	else process->next = queue->head;
	queue->head = process;
	queue->length++;
	return queue->length;	
}
int insertProcessHere(schedulerQueue *queue,Process *previous,Process *process ,Process *next){
	previous->next = process;
	process->next = next;
	return ++queue->length;
}
int insertProcess(schedulerQueue *queue, Process *process){
	Process *previous,*next,*temp;
	temp = queue->head;
	if(queue->length == 0)		
		return insertAtStart(queue, process);
	if(process->pPriority < temp->pPriority)
		return insertAtStart(queue, process);
	// printf("%p\n", temp->next);
	for(;temp != NULL;temp = temp->next){
		previous = temp;
		next = temp->next;
		if(process->pPriority < next->pPriority)
			return insertProcessHere(queue ,previous, process ,next);
	};
	
	// for(temp = queue->head;temp->next != NULL;temp = temp->next){
	// 	previous = temp;
	// 	next = temp->next;
	// 	if(process->pPriority < temp->pPriority)
	// 		return insertProcessHere(queue ,previous, process,next);
	// };
	// insertProcess(schedulerQueue *queue, Process *process)
	return 0;
}

void dispose(schedulerQueue *queue){
	free(queue);
}