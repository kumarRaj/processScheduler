#include "schedulerQueue.h"
#include <stdlib.h>
#include <string.h>
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
	Process *previous,*next,*temp;int i = 0;
	temp = queue->head;
	if(queue->length == 0)		
		return insertAtStart(queue, process);
	if(process->pPriority < temp->pPriority)
		return insertAtStart(queue, process);
	for(;temp->next != NULL;temp = temp->next){
		previous = temp;
		next = temp->next;
		if(process->pPriority < next->pPriority)
			return insertProcessHere(queue ,previous, process ,next);
	};
	temp->next = process;
	process->next = NULL;
	return ++queue->length;
}
int removeProcessHere(schedulerQueue *queue,Process *previous ,Process *next){
	previous->next = next->next;
	return --queue->length;
}

int removeProcess(schedulerQueue *queue){
	Process *temp,*previous,*next;int i = 0;
	temp = queue->head;
	if(queue->length == 1){
		if(temp->pTime == 0)
			queue->head = NULL;
		return --queue->length;
	}
	for(;temp->next != NULL;temp = temp->next){
		previous = temp;
		next = temp->next;
		if(next->pTime == 0)
			return removeProcessHere(queue ,previous ,next);
	}
	if(NULL == temp->next){
		previous->next = NULL;
		return --queue->length;
	};
	return 0;
}
void dispose(schedulerQueue *queue){
	free(queue);
}