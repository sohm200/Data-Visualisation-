# Automated Data Visualization Dashboard: CI/CD Pipeline

**CCA 2: CI/CD Pipeline Implementation and Deployment of an Existing Project**
TYCSE, Cloud Computing and DevOps

## 1. The project

An existing academic project from the Software Engineering course: a **Flask** web app. A user uploads an Excel or CSV file, and the app profiles the data, picks suitable chart types and renders an interactive **Plotly** dashboard. It has a full SRS and a 177-test **pytest** suite.

This repository adds a complete **CI/CD pipeline** around it: every push to GitHub is built, tested, containerised, published to Docker Hub and deployed to Kubernetes (Minikube) on AWS, automatically.

## 2. Architecture

```
Developer --git push--> GitHub --poll SCM--> Jenkins (AWS EC2)
                                                |
              1 Checkout -> 2 Build & Test (pytest) -> 3 Docker Build
                                                |
                                  4 Push image --> Docker Hub
                                                |
              5 kubectl apply (Deployment + Service) --> Minikube (on EC2)
                                                |
                              6 Verify --> app at http://<EC2-IP>:30080
```

| Tool | Role |
|---|---|
| GitHub | Stores code, Dockerfile, Jenkinsfile, `k8s/` manifests |
| AWS EC2 (`c7i-flex.large`, Ubuntu 24.04, 4 GB RAM) | Hosts Jenkins, Docker and Minikube |
| Jenkins | Runs the pipeline from the `Jenkinsfile` |
| Docker | Packages the app into an image |
| Docker Hub | Registry; Kubernetes pulls the image from here |
| Minikube + kubectl | Local Kubernetes cluster and its CLI |

## 3. Repository layout

| File | Purpose |
|---|---|
| `Dockerfile` | Builds the image (python:3.12-slim, installs `requirements.txt`, runs `app.py`) |
| `Jenkinsfile` | Declarative pipeline, 6 stages |
| `k8s/deployment.yaml` | Kubernetes **Deployment** (1 replica, port 5000) |
| `k8s/service.yaml` | Kubernetes **Service** (NodePort 30080 -> 5000) |
| `setup-ec2.sh` | One-shot script that installs Docker, Jenkins, kubectl, Minikube on EC2 |
| `app.py`, `*.py`, `templates/`, `static/`, `tests/` | The application and its tests |

## 4. Pipeline stages (`Jenkinsfile`)

| # | Stage | What it does |
|---|---|---|
| 1 | **Checkout** | Jenkins pulls the latest code from GitHub (`checkout scm`) |
| 2 | **Build and Test** | Creates a virtualenv, installs dependencies, runs `pytest` (177 tests). A failure stops the pipeline |
| 3 | **Docker Build** | `docker build` creates the image, tagged with the Jenkins build number (e.g. `:2`) and `:latest` |
| 4 | **Push Image** | Logs in with the stored credential and pushes both tags to Docker Hub |
| 5 | **Deploy to Minikube** | Substitutes the new image tag into the Deployment, runs `kubectl apply` on the Deployment and Service, waits for `kubectl rollout status` |
| 6 | **Verify** | Runs `kubectl get pods`, `get deployment`, `get service`, then `curl`s the app |

A **Poll SCM** trigger checks GitHub every 2 minutes, so a push starts the pipeline with no manual step.

## 5. Setting up Jenkins on AWS

1. Launched an EC2 instance: Ubuntu 24.04, `c7i-flex.large` (2 vCPU, 4 GB RAM), 20 GB disk. Smaller instances run out of memory when Jenkins and Minikube share them.
2. **Security group** inbound rules: 22 (SSH), 8080 (Jenkins), 30080 (the app).
3. Connected over SSH with the key pair and ran `setup-ec2.sh`. It installs Docker, Java 21, Jenkins (heap capped at 768 MB), kubectl and Minikube (Docker driver), starts Minikube as the `jenkins` user, and forwards public port 30080 to the Minikube NodePort.
4. Opened `http://<EC2-IP>:8080`, unlocked Jenkins and installed the suggested plugins (Git, Pipeline).
5. Added a **Username with password** credential with ID `dockerhub`: Docker Hub username plus an access token with Read & Write permission.
6. Created a **Pipeline** job, definition *Pipeline script from SCM*, pointing at this repository, branch `main`, script path `Jenkinsfile`.

## 6. Pushing the image

The `Push Image` stage uses `withCredentials` to read the `dockerhub` credential, so the token is never written in the repository and is masked in the console log. It runs `docker login --password-stdin`, then pushes `<dockerhub-user>/dashboard:<build-number>` and `:latest`. Each build gets a unique, traceable tag.

## 7. Deploying and accessing the app

- `k8s/deployment.yaml` holds a placeholder image name. The Deploy stage replaces it with the freshly pushed tag, so Minikube pulls the new image **from Docker Hub**, not from the local machine.
- `k8s/service.yaml` is a **NodePort** Service on port 30080.
- Verify on the EC2 instance:
  ```
  kubectl get pods,deploy,svc
  ```
- Open the app at `http://<EC2-public-IP>:30080`.

## 8. Second run: demonstrating redeployment

I changed the heading in `templates/upload.html` to **"Automated Data Visualization Dashboard (v2 - deployed via Jenkins)"** and pushed it to GitHub. Jenkins started build #2 automatically and ran every stage again. It pushed image tag `2`, and Kubernetes performed a **rolling update**: a new pod started with the new image and the old pod was terminated. Refreshing the browser showed the new heading with no manual deployment step.

## 9. Running locally (without CI/CD)

```
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000
python -m pytest       # run the tests (needs requirements-dev.txt)
```
