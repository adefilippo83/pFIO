# pFIO

parallel Flexible I/O

[ ![Codeship Status for adefilippo83/pFIO](https://codeship.com/projects/5d654350-6f79-0133-76f6-7ae947dfb2ee/status?branch=master)](https://codeship.com/projects/116241)

pFIO is a python tool that will spawn a number of fio processes on multiple hosts aggregating the results.
It doesn't use the built-in client-server method cause it's pretty difficult to manage and orchestrate.
pFIO uses the paramiko python library in order to run FIO on multiple hosts.
