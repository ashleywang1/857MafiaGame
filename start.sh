pkill -f '[Pp]ython.? mafia.py'&
wait $!

ports=$(echo {8870..8880} | sed 's/ /,/g')
for i in {0..10}; do
  python3 mafia.py $ports $i &
done
