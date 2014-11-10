#!/bin/bash
cd ..
while [ 1 ] 
do
  echo "Running...instance bids tasks"
  curl -s http://0.0.0.0:8079/tasks/instancebids/

  echo "Running...instance tasks"
  curl -s http://0.0.0.0:8079/tasks/instances/

  echo "Running...wisp tasks"
  curl -s http://0.0.0.0:8079/tasks/wisps/

  echo "Running in 60"
  sleep 30
  echo "Running in 30"
  sleep 15
  echo "Running in 15"
  sleep 5
  echo "Running in 10"
  sleep 5
  echo "Running in 5"
  sleep 2
  echo "Running in 3"
  sleep 1
  echo "Running in 2"
  sleep 1
  echo "Running in 1"
  sleep 1
done
