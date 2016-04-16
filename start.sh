pkill -f 'python2 mafia.py'&
#kill -9 $(ps -ea | grep mafia)&
wait $!
for i in {0..10}; do
  python2 mafia.py '8870, 8871, 8872, 8873, 8874, 8875, 8876, 8877, 8878, 8879, 8880' $i &
done
