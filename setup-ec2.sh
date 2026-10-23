#!/usr/bin/env bash
# One-shot setup for a fresh Ubuntu 22.04/24.04 EC2 instance (t3.medium, 20 GB disk).
# Installs Docker, Jenkins, kubectl, Minikube and exposes the app on port 30080.
# Run once:  bash setup-ec2.sh
set -euo pipefail

echo "== 1. Swap (2 GB safety net for Jenkins + Minikube) =="
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
fi

sudo rm -f /etc/apt/sources.list.d/jenkins.list /etc/apt/keyrings/jenkins-keyring.asc   # clear any stale Jenkins repo from an earlier failed run
echo "== 2. Base packages, Docker, Java, Python, socat =="
sudo apt-get update -y
sudo apt-get install -y docker.io openjdk-17-jre-headless python3-venv python3-pip curl socat ca-certificates gnupg
sudo systemctl enable --now docker

echo "== 3. Jenkins =="
sudo mkdir -p /etc/apt/keyrings
sudo curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key -o /etc/apt/keyrings/jenkins-keyring.asc
echo "deb [signed-by=/etc/apt/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" \
  | sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y jenkins
# Cap Jenkins' heap so it leaves RAM for Minikube
sudo mkdir -p /etc/systemd/system/jenkins.service.d
printf '[Service]\nEnvironment="JAVA_OPTS=-Xmx768m -Djava.awt.headless=true"\n' \
  | sudo tee /etc/systemd/system/jenkins.service.d/memory.conf > /dev/null
sudo usermod -aG docker jenkins
sudo usermod -aG docker "$USER"

echo "== 4. kubectl and Minikube =="
curl -fsSLo /tmp/kubectl "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -m 0755 /tmp/kubectl /usr/local/bin/kubectl
curl -fsSLo /tmp/minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install -m 0755 /tmp/minikube /usr/local/bin/minikube

echo "== 5. Restart Jenkins (picks up docker group + memory cap) =="
sudo systemctl daemon-reload
sudo systemctl enable jenkins
sudo systemctl restart jenkins

echo "== 6. Start Minikube as the jenkins user (so pipeline jobs can use kubectl) =="
sudo -u jenkins -H minikube start --driver=docker --cpus=2 --memory=2200mb
sudo -u jenkins -H kubectl get nodes

echo "== 7. Forward public port 30080 -> Minikube NodePort =="
MINIKUBE_IP=$(sudo -u jenkins -H minikube ip)
sudo tee /etc/systemd/system/app-forward.service > /dev/null <<UNIT
[Unit]
Description=Forward :30080 to the Minikube NodePort
After=network.target

[Service]
ExecStart=/usr/bin/socat TCP-LISTEN:30080,fork,reuseaddr TCP:${MINIKUBE_IP}:30080
Restart=always

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now app-forward

echo
echo "== DONE =="
echo "Jenkins:  http://<EC2-public-IP>:8080"
echo "Unlock password:"
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
echo "App (after first pipeline run): http://<EC2-public-IP>:30080"
echo "If the instance is ever rebooted, run:  sudo -u jenkins -H minikube start"
