pipeline {
    agent any

    environment {
        IMAGE_NAME = 'dashboard'
        IMAGE_TAG  = "${BUILD_NUMBER}"
    }

    triggers {
        pollSCM('H/2 * * * *')   // check GitHub every ~2 minutes; builds only if there is a new commit
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build and Test') {
            steps {
                sh '''
                    python3 -m venv .ci-venv
                    . .ci-venv/bin/activate
                    pip install -q -r requirements-dev.txt
                    python -m pytest
                '''
            }
        }

        stage('Docker Build') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
                    sh 'docker build -t $DH_USER/$IMAGE_NAME:$IMAGE_TAG -t $DH_USER/$IMAGE_NAME:latest .'
                }
            }
        }

        stage('Push Image') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
                    sh '''
                        echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
                        docker push $DH_USER/$IMAGE_NAME:$IMAGE_TAG
                        docker push $DH_USER/$IMAGE_NAME:latest
                    '''
                }
            }
        }

        stage('Deploy to Minikube') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
                    sh '''
                        sed -i "s|IMAGE_PLACEHOLDER|$DH_USER/$IMAGE_NAME:$IMAGE_TAG|" k8s/deployment.yaml
                        kubectl apply -f k8s/deployment.yaml
                        kubectl apply -f k8s/service.yaml
                        kubectl rollout status deployment/dashboard --timeout=120s
                    '''
                }
            }
        }

        stage('Verify') {
            steps {
                sh '''
                    kubectl get pods
                    kubectl get deployment dashboard
                    kubectl get service dashboard
                    curl -sf "http://$(minikube ip):30080/" > /dev/null && echo "App is reachable"
                '''
            }
        }
    }
}
