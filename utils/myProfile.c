#include <sys/time.h>
#include <stdlib.h>
#include <stdio.h>

int main(int argc, char* argv[]){
	if (argc < 4){
		printf("Usage: $> myProfile -o outputFile targetApplication <application arguments>\n");
		return 1;
	}
	
	if(strcmp(argv[1],"-o")){
		printf("Usage: $> myProfile -o outputFile targetApplication <application arguments>\n");
		return 1;
	}
	
	FILE* foutput = fopen(argv[2],"w");
	if(!foutput){
		printf("Error: cannot open %s\n",argv[2]);
		return 1;
	}
	
	char command[256];
	sprintf(command,"");
	int a;
	for(a = 3; a < argc; a++){
		sprintf(command,"%s %s",command,argv[a]);
	}
	
	struct timeval start, end;
	gettimeofday(&start,NULL);
	
	system(command);
	
	gettimeofday(&end,NULL);

	unsigned long time_ms = (end.tv_sec - start.tv_sec)*1000 + (end.tv_usec - start.tv_usec)/1000;
	
	fprintf(foutput,"Execution time: %lu ms\n",time_ms);
	fclose(foutput);
	return 0;
}
