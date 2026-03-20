1- ejecutar el siguiente comando y loguear con la cuenta gcloud@pagoflex.com.ar 

gcloud auth login

2- ejecutar el siguiente comando y loguear con la cuenta gcloud@pagoflex.com.ar 

gcloud auth application-default login

3- en la carpeta root donde se encuentra el dockerfile ejecutar este comando genera la imagen docker en local 

docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/pagoflex-middleware/pagoflex-middleware/pagoflex:latest .

4- ejecutar el comando para pushear la imagen docker a gcp

docker push us-central1-docker.pkg.dev/pagoflex-middleware/pagoflex-middleware/pagoflex:latest

5- ejecutar comando de deploy

gcloud run services update pagoflex-middleware-api --image us-central1-docker.pkg.dev/pagoflex-middleware/pagoflex-middleware/pagoflex:latest --region us-central1

...