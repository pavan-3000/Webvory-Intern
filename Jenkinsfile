pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "${JOB_NAME.toLowerCase().replaceAll('[^a-z0-9-]', '-')}"
        DOCKER_TAG   = "${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Docker Build') {
            when { expression { return fileExists('Dockerfile') } }
            steps {
                script {
                    def dockerAvailable = sh(script: 'which docker 2>/dev/null || test -x /usr/bin/docker', returnStatus: true) == 0
                    if (dockerAvailable) {
                        def daemonOk = sh(script: 'docker info > /dev/null 2>&1', returnStatus: true) == 0
                        if (daemonOk) {
                            retry(2) {
                                sh "docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} ."
                            }
                            sh "docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest"
                        } else {
                            echo 'Docker daemon not reachable — run: docker exec jenkins chmod 666 /var/run/docker.sock'
                        }
                    } else {
                        echo 'Docker not available — install Docker in the Jenkins image or mount the socket'
                    }
                }
            }
        }

        stage('Trivy Scan') {
            when { expression { return fileExists('Dockerfile') } }
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    script {
                        withEnv(["PATH+DEVPILOT=${env.HOME}/devpilot-tools/bin"]) {
                            def trivyOk = sh(script: 'which trivy 2>/dev/null', returnStatus: true) == 0
                            if (trivyOk) {
                                sh "trivy image --exit-code 0 --severity HIGH,CRITICAL --format table ${DOCKER_IMAGE}:${DOCKER_TAG} | tee trivy-report.txt"
                                archiveArtifacts artifacts: 'trivy-report.txt', allowEmptyArchive: true
                            } else {
                                echo 'Trivy not available — skipping scan'
                            }
                        }
                    }
                }
            }
        }

        stage('Push to Registry') {
            when { expression { return fileExists('Dockerfile') } }
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    script {
                        withCredentials([usernamePassword(credentialsId: 'devpilot-registry-1782053771939', usernameVariable: 'REG_USER', passwordVariable: 'REG_PASS')]) {
                            sh '''
                                BRANCH_TAG=$(echo ${GIT_BRANCH:-${BRANCH_NAME:-main}} | sed 's|origin/||' | tr '/' '-' | tr '[:upper:]' '[:lower:]')
                                echo $REG_PASS | docker login -u $REG_USER --password-stdin
                                docker tag $DOCKER_IMAGE:$DOCKER_TAG pav30/webvory-intern:$DOCKER_TAG-$BRANCH_TAG
                                docker push pav30/webvory-intern:$DOCKER_TAG-$BRANCH_TAG
                            '''
                        }
                    }
                }
            }
        }

        stage('Deploy to VM') {
            when { expression { return fileExists('Dockerfile') } }
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    script {
                        withCredentials([sshUserPrivateKey(credentialsId: 'devpilot-deploy-pavan-3000-Webvory-Intern-master', keyFileVariable: 'SSH_KEY'), usernamePassword(credentialsId: 'devpilot-registry-1782053771939', usernameVariable: 'REG_USER', passwordVariable: 'REG_PASS')]) {
                            sh '''
                                BRANCH_TAG=$(echo ${GIT_BRANCH:-${BRANCH_NAME:-main}} | sed 's|origin/||' | tr '/' '-' | tr '[:upper:]' '[:lower:]')
                                FULL_IMAGE="pav30/webvory-intern:$DOCKER_TAG-$BRANCH_TAG"
                                REG_PASS_B64=$(echo -n "$REG_PASS" | base64 -w0)
                                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.159.57.103 "echo $REG_PASS_B64 | base64 -d | docker login -u $REG_USER --password-stdin"
                                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=30 ubuntu@54.159.57.103 "docker pull $FULL_IMAGE && (docker stop webvory-intern 2>/dev/null; docker rm webvory-intern 2>/dev/null; docker run -d --name webvory-intern --restart unless-stopped -p 8000:8000 $FULL_IMAGE) && echo Deploy OK"
                                echo "Deployed: $FULL_IMAGE → http://54.159.57.103:8000"
                            '''
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            script {
                def status = currentBuild.result ?: 'IN_PROGRESS'
                def promptText = "Analyze this Jenkins CI/CD build and give 2-3 actionable bullet points: what passed, what failed (if any), and one improvement.\nJob: ${env.JOB_NAME} Build#${env.BUILD_NUMBER} Branch: ${env.GIT_BRANCH ?: env.BRANCH_NAME ?: 'unknown'} Status: ${status}"
                def aiDone = false

                for (def credId : ['devpilot-anthropic-key', 'ANTHROPIC_API_KEY']) {
                    if (aiDone) break
                    try {
                        withCredentials([string(credentialsId: credId, variable: 'ANTHROPIC_KEY')]) {
                            writeFile file: '.ai-payload.json', text: groovy.json.JsonOutput.toJson([
                                model: 'claude-haiku-4-5-20251001',
                                max_tokens: 350,
                                messages: [[role: 'user', content: promptText]]
                            ])
                            def rc = sh returnStatus: true, script: '''
                                curl -sf -X POST https://api.anthropic.com/v1/messages \
                                  -H 'Content-Type: application/json' \
                                  -H "x-api-key: $ANTHROPIC_KEY" \
                                  -H 'anthropic-version: 2023-06-01' \
                                  --max-time 30 \
                                  -d @.ai-payload.json \
                                  -o .ai-response.json
                            '''
                            if (rc == 0) {
                                def resp = new groovy.json.JsonSlurper().parseText(readFile('.ai-response.json'))
                                echo "\n=== Claude AI Build Analysis ===\n${resp.content[0].text}\n================================"
                                writeFile file: 'ai-analysis.json', text: readFile('.ai-response.json')
                                archiveArtifacts artifacts: 'ai-analysis.json', allowEmptyArchive: true
                                aiDone = true
                            }
                        }
                    } catch (ignored) {}
                }

                for (def credId : ['devpilot-openai-key', 'OPENAI_API_KEY']) {
                    if (aiDone) break
                    try {
                        withCredentials([string(credentialsId: credId, variable: 'OPENAI_KEY')]) {
                            writeFile file: '.ai-payload.json', text: groovy.json.JsonOutput.toJson([
                                model: 'gpt-4o-mini',
                                max_tokens: 350,
                                messages: [[role: 'user', content: promptText]]
                            ])
                            def rc = sh returnStatus: true, script: '''
                                curl -sf -X POST https://api.openai.com/v1/chat/completions \
                                  -H 'Content-Type: application/json' \
                                  -H "Authorization: Bearer $OPENAI_KEY" \
                                  --max-time 30 \
                                  -d @.ai-payload.json \
                                  -o .ai-response.json
                            '''
                            if (rc == 0) {
                                def resp = new groovy.json.JsonSlurper().parseText(readFile('.ai-response.json'))
                                echo "\n=== ChatGPT Build Analysis ===\n${resp.choices[0].message.content}\n==============================="
                                writeFile file: 'ai-analysis.json', text: readFile('.ai-response.json')
                                archiveArtifacts artifacts: 'ai-analysis.json', allowEmptyArchive: true
                                aiDone = true
                            }
                        }
                    } catch (ignored) {}
                }

                if (!aiDone) {
                    echo 'AI analysis skipped — configure an API key in DevPilot Settings (Claude or ChatGPT)'
                }
            }
        }
        success { echo 'Pipeline succeeded!' }
        failure  { echo 'Pipeline failed!' }
    }
}