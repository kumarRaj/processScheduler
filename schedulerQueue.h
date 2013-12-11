typedef struct{
	int running;
	int wait;
	int end;
} Status;
typedef struct p{
	char pname[256];
	int pTime;
	Status pStatus;
	int pPriority;
	struct p *next;
} Process;

typedef struct{
	Process *head;
	int length;
} schedulerQueue;

schedulerQueue* create();
int insertProcess(schedulerQueue *queue,Process *process);
int removeProcess(schedulerQueue *queue);
void dispose(schedulerQueue *queue);