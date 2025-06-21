.PHONY: activate server-up start

activate:
	@conda activate lkcc

server-up:
	@echo "Starting the benchmark server"
	@./launch.sh
