pipeline {
    agent any

    environment {
        K8S_NAMESPACE = 'blue-green-demo'
        DOCKER_IMAGE = 'priyam101/blue-green-demo'
        SERVICE_NAME = 'blue-green-service'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo 'Source code checked out successfully.'
            }
        }

        stage('Identify Active Environment') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'blue-green-kubeconfig',
                        variable: 'KUBE_CONFIG_FILE'
                    )
                ]) {
                    script {
                        env.KUBECONFIG = KUBE_CONFIG_FILE

                        def active = sh(
                            script: """
                                kubectl --kubeconfig="\$KUBECONFIG" \
                                get service ${SERVICE_NAME} \
                                -n ${K8S_NAMESPACE} \
                                -o jsonpath='{.spec.selector.version}'
                            """,
                            returnStdout: true
                        ).trim()

                        if (!(active in ['blue', 'green'])) {
                            error("Unknown active environment: ${active}")
                        }

                        env.ACTIVE_COLOR = active
                        env.TARGET_COLOR =
                            active == 'blue' ? 'green' : 'blue'

                        env.TARGET_DEPLOYMENT =
                            "${env.TARGET_COLOR}-deployment"

                        env.TARGET_CONTAINER =
                            "${env.TARGET_COLOR}-container"

                        env.APP_VERSION = "1.0.${env.BUILD_NUMBER}"

                        echo "Currently active: ${env.ACTIVE_COLOR}"
                        echo "Deploying to: ${env.TARGET_COLOR}"
                    }
                }
            }
        }

        stage('Build and Push Docker Image') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {
                    sh '''
                        set -eu

                        echo "Building Docker image..."

                        docker build \
                            -t "$DOCKER_IMAGE:$BUILD_NUMBER" .

                        echo "Logging in to Docker Hub..."

                        echo "$DOCKER_PASS" | docker login \
                            -u "$DOCKER_USER" --password-stdin

                        docker push "$DOCKER_IMAGE:$BUILD_NUMBER"

                        docker logout
                    '''
                }
            }
        }

        stage('Deploy to Inactive Environment') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'blue-green-kubeconfig',
                        variable: 'KUBE_CONFIG_FILE'
                    )
                ]) {
                    sh '''
                        set -eu

                        export KUBECONFIG="$KUBE_CONFIG_FILE"

                        echo "Deploying to $TARGET_COLOR..."

                        kubectl set image \
                            deployment/$TARGET_DEPLOYMENT \
                            $TARGET_CONTAINER=$DOCKER_IMAGE:$BUILD_NUMBER \
                            -n $K8S_NAMESPACE

                        kubectl set env \
                            deployment/$TARGET_DEPLOYMENT \
                            APP_VERSION=$APP_VERSION \
                            APP_COLOR=$TARGET_COLOR \
                            -n $K8S_NAMESPACE

                        kubectl patch deployment $TARGET_DEPLOYMENT \
                            -n $K8S_NAMESPACE \
                            --type=strategic \
                            -p="{\\"spec\\":{\\"template\\":{\\"spec\\":{\\"containers\\":[{\\"name\\":\\"$TARGET_CONTAINER\\",\\"imagePullPolicy\\":\\"Always\\"}]}}}}"

                        kubectl rollout status \
                            deployment/$TARGET_DEPLOYMENT \
                            -n $K8S_NAMESPACE \
                            --timeout=180s
                    '''
                }
            }
        }

        stage('Health Check') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'blue-green-kubeconfig',
                        variable: 'KUBE_CONFIG_FILE'
                    )
                ]) {
                    sh '''
                        set -eu

                        export KUBECONFIG="$KUBE_CONFIG_FILE"

                        echo "Testing inactive environment..."

                        kubectl port-forward \
                            deployment/$TARGET_DEPLOYMENT \
                            18080:5000 \
                            -n $K8S_NAMESPACE \
                            >/tmp/blue-green-port-forward.log 2>&1 &

                        PF_PID=$!

                        trap 'kill $PF_PID 2>/dev/null || true' EXIT

                        HEALTHY=false

                        for i in $(seq 1 20); do
                            if curl -fsS http://127.0.0.1:18080/health; then
                                HEALTHY=true
                                break
                            fi

                            sleep 2
                        done

                        if [ "$HEALTHY" != "true" ]; then
                            echo "Health check failed."
                            cat /tmp/blue-green-port-forward.log
                            exit 1
                        fi

                        echo "Health check passed!"
                    '''
                }
            }
        }

        stage('Switch Traffic') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'blue-green-kubeconfig',
                        variable: 'KUBE_CONFIG_FILE'
                    )
                ]) {
                    sh '''
                        set -eu

                        export KUBECONFIG="$KUBE_CONFIG_FILE"

                        echo "Switching traffic to $TARGET_COLOR..."

                        kubectl patch service $SERVICE_NAME \
                            -n $K8S_NAMESPACE \
                            --type merge \
                            -p="{\\"spec\\":{\\"selector\\":{\\"app\\":\\"blue-green-app\\",\\"version\\":\\"$TARGET_COLOR\\"}}}"

                        echo "Traffic successfully switched!"
                    '''
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'blue-green-kubeconfig',
                        variable: 'KUBE_CONFIG_FILE'
                    )
                ]) {
                    sh '''
                        set -eu

                        export KUBECONFIG="$KUBE_CONFIG_FILE"

                        echo "Final Service selector:"

                        kubectl get service $SERVICE_NAME \
                            -n $K8S_NAMESPACE \
                            -o jsonpath='{.spec.selector}'

                        echo ""

                        echo "Final deployment status:"

                        kubectl get deployments \
                            -n $K8S_NAMESPACE
                    '''
                }
            }
        }
    }

    post {
    success {
        echo "BLUE-GREEN DEPLOYMENT SUCCESSFUL!"
        echo "Previous environment: ${env.ACTIVE_COLOR}"
        echo "New active environment: ${env.TARGET_COLOR}"
    }

    failure {
        echo "DEPLOYMENT FAILED!"

        script {
            if (env.ACTIVE_COLOR in ['blue', 'green']) {
                echo "Restoring traffic to ${env.ACTIVE_COLOR}..."

                withCredentials([
                    file(
                        credentialsId: 'blue-green-kubeconfig',
                        variable: 'KUBE_CONFIG_FILE'
                    )
                ]) {
                    def rollbackStatus = sh(
                        script: '''
                            kubectl --kubeconfig="$KUBE_CONFIG_FILE" \
                                patch service blue-green-service \
                                -n blue-green-demo \
                                --type merge \
                                -p="{\\"spec\\":{\\"selector\\":{\\"app\\":\\"blue-green-app\\",\\"version\\":\\"$ACTIVE_COLOR\\"}}}"
                        ''',
                        returnStatus: true
                    )

                    if (rollbackStatus == 0) {
                        echo "Rollback successful. Previous environment restored."
                    } else {
                        echo "WARNING: Automatic rollback failed. Manual verification required."
                    }
                }
            }
        }
    }
}
}
