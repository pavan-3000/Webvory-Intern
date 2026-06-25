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

        stage('Setup Tools') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    sh '''
                        TOOLS_DIR="$HOME/devpilot-tools"
                        mkdir -p "$TOOLS_DIR/bin"

                        if ! which docker 2>/dev/null && [ ! -x "$TOOLS_DIR/bin/docker" ]; then
                            DOCKER_VERSION=24.0.7
                            curl -fsSL "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz" -o /tmp/docker-cli.tgz 2>/dev/null || true
                            tar -xz -C /tmp -f /tmp/docker-cli.tgz 2>/dev/null || true
                            mv /tmp/docker/docker "$TOOLS_DIR/bin/docker" 2>/dev/null || true
                            rm -rf /tmp/docker-cli.tgz /tmp/docker 2>/dev/null || true
                        fi

                        if ! which trivy 2>/dev/null && [ ! -x "$TOOLS_DIR/bin/trivy" ]; then
                            curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b "$TOOLS_DIR/bin" 2>/dev/null || true
                        fi
                    '''
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    script {
                        def sonarOk = sh(script: 'which sonar-scanner 2>/dev/null', returnStatus: true) == 0
                        if (sonarOk) {
                            withSonarQubeEnv('SonarQube') {
                                sh 'sonar-scanner -Dsonar.projectKey=${env.JOB_NAME} -Dsonar.sources=. -Dsonar.host.url=${SONAR_HOST_URL}'
                            }
                        } else {
                            echo 'sonar-scanner not found — configure SonarQube Scanner in Jenkins → Manage Jenkins → Tools'
                        }
                    }
                }
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
                                docker tag $DOCKER_IMAGE:$DOCKER_TAG pav30/webvory-intern-frontend:$DOCKER_TAG-$BRANCH_TAG
                                docker push pav30/webvory-intern-frontend:$DOCKER_TAG-$BRANCH_TAG
                            '''
                        }
                    }
                }
            }
        }

        stage('Deploy to VM') {
            when { expression { return fileExists('Dockerfile') } }
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    script {
                        withCredentials([sshUserPrivateKey(credentialsId: 'devpilot-deploy-pavan-3000-Webvory-Intern-master', keyFileVariable: 'SSH_KEY'), usernamePassword(credentialsId: 'devpilot-registry-1782053771939', usernameVariable: 'REG_USER', passwordVariable: 'REG_PASS')]) {
                            sh '''
                                BRANCH_TAG=$(echo ${GIT_BRANCH:-${BRANCH_NAME:-main}} | sed 's|origin/||' | tr '/' '-' | tr '[:upper:]' '[:lower:]')
                                REG_PASS_B64=$(echo -n "$REG_PASS" | base64 -w0)
                                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.221.68.17 "echo $REG_PASS_B64 | base64 -d | docker login -u $REG_USER --password-stdin"
                                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.221.68.17 "mkdir -p ~/devpilot-app && echo 'IyBBcHBsaWNhdGlvbgpBUFBfRU5WPXByb2R1Y3Rpb24KQVBQX1NFQ1JFVF9LRVk9Y2hhbmdlLW1lLXRvLWEtcmFuZG9tLXNlY3JldC1rZXktYXQtbGVhc3QtMzItY2hhcnMKQVBQX0RFQlVHPWZhbHNlCkFQUF9QT1JUPTgwMDAKCiMgUG9zdGdyZVNRTApQT1NUR1JFU19IT1NUPXBvc3RncmVzClBPU1RHUkVTX1BPUlQ9NTQzMgpQT1NUR1JFU19EQj1hcHBkYgpQT1NUR1JFU19VU0VSPWFwcHVzZXIKUE9TVEdSRVNfUEFTU1dPUkQ9Y2hhbmdlLW1lLXN0cm9uZy1wYXNzd29yZAoKIyBSZWRpcwpSRURJU19IT1NUPXJlZGlzClJFRElTX1BPUlQ9NjM3OQpSRURJU19QQVNTV09SRD1jaGFuZ2UtbWUtcmVkaXMtcGFzc3dvcmQKUkVESVNfVFRMPTMwMAoKIyBOR0lOWCAvIFNTTApET01BSU49d2Vidm9yeS1pbnRlcm4uZGV2bGF1Y2guY29t' | base64 -d > ~/devpilot-app/frontend.env"
                                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.221.68.17 "pip3 install pyyaml -q 2>/dev/null || true; echo \"aW1wb3J0IHlhbWwsIHN5cywgb3MsIGZjbnRsCnBhdGggPSBvcy5wYXRoLmV4cGFuZHVzZXIoJ34vZGV2cGlsb3QtYXBwL2RvY2tlci1jb21wb3NlLnltbCcpCnRhZyA9IHN5cy5hcmd2WzFdCm9zLm1ha2VkaXJzKG9zLnBhdGguZXhwYW5kdXNlcignfi9kZXZwaWxvdC1hcHAnKSwgZXhpc3Rfb2s9VHJ1ZSkKbGYgPSBvcGVuKG9zLnBhdGguZXhwYW5kdXNlcignfi9kZXZwaWxvdC1hcHAvLmRldnBpbG90LmxvY2snKSwgJ3cnKQpmY250bC5mbG9jayhsZiwgZmNudGwuTE9DS19FWCkKdHJ5OgogdHJ5OgogIHdpdGggb3BlbihwYXRoKSBhcyBmOiBkYXRhID0geWFtbC5zYWZlX2xvYWQoZikgb3Ige30KIGV4Y2VwdCBFeGNlcHRpb246CiAgZGF0YSA9IHt9CiBpZiBub3QgaXNpbnN0YW5jZShkYXRhLmdldCgnc2VydmljZXMnKSwgZGljdCk6IGRhdGFbJ3NlcnZpY2VzJ10gPSB7fQogZXhpc3RpbmcgPSBkYXRhWydzZXJ2aWNlcyddLmdldCgnZnJvbnRlbmQnKQogcHJpbnQoJ1tkZXZwaWxvdF0gc2VydmljZT1mcm9udGVuZCBleGlzdGluZz0nICsgc3RyKGV4aXN0aW5nIGlzIG5vdCBOb25lKSkKIGlmIGV4aXN0aW5nOgogIHByaW50KCdbZGV2cGlsb3RdIG9sZCBpbWFnZT0nICsgc3RyKGV4aXN0aW5nLmdldCgnaW1hZ2UnKSkgKyAnIG9sZCBwb3J0cz0nICsgc3RyKGV4aXN0aW5nLmdldCgncG9ydHMnKSkpCiAgZXhpc3RpbmdbJ2ltYWdlJ10gPSAncGF2MzAvd2Vidm9yeS1pbnRlcm4tZnJvbnRlbmQ6JyArIHRhZwogIGV4aXN0aW5nWydjb250YWluZXJfbmFtZSddID0gJ2Zyb250ZW5kJwogIGV4aXN0aW5nWydwb3J0cyddID0gWyc4MDAwOjgwMDAnXQogIHByaW50KCdbZGV2cGlsb3RdIG5ldyBpbWFnZT0nICsgZXhpc3RpbmdbJ2ltYWdlJ10gKyAnIG5ldyBwb3J0cz0nICsgc3RyKGV4aXN0aW5nLmdldCgncG9ydHMnKSkpCiAgZGF0YVsnc2VydmljZXMnXVsnZnJvbnRlbmQnXSA9IGV4aXN0aW5nCiBlbHNlOgogIHByaW50KCdbZGV2cGlsb3RdIGNyZWF0aW5nIG5ldyBzZXJ2aWNlIGJsb2NrJykKICBzdmMgPSB7J2ltYWdlJzogJ3BhdjMwL3dlYnZvcnktaW50ZXJuLWZyb250ZW5kOicgKyB0YWcsICdjb250YWluZXJfbmFtZSc6ICdmcm9udGVuZCcsICdyZXN0YXJ0JzogJ3VubGVzcy1zdG9wcGVkJ30KICBzdmNbJ3BvcnRzJ10gPSBbJzgwMDA6ODAwMCddCiAgc3ZjWydlbnZfZmlsZSddID0gWyd+L2RldnBpbG90LWFwcC9mcm9udGVuZC5lbnYnXQogIHByaW50KCdbZGV2cGlsb3RdIG5ldyBzZXJ2aWNlIHBvcnRzPScgKyBzdHIoc3ZjLmdldCgncG9ydHMnKSkpCiAgZGF0YVsnc2VydmljZXMnXVsnZnJvbnRlbmQnXSA9IHN2YwogaWYgbm90IGRhdGFbJ3NlcnZpY2VzJ10uZ2V0KCdwb3N0Z3JlcycpOgogIGRhdGFbJ3NlcnZpY2VzJ11bJ3Bvc3RncmVzJ10gPSB7J2ltYWdlJzogJ3Bvc3RncmVzOjE2LWFscGluZScsICdlbnZpcm9ubWVudCc6IHsnUE9TVEdSRVNfREInOiAnYXBwZGInLCAnUE9TVEdSRVNfVVNFUic6ICdhcHB1c2VyJywgJ1BPU1RHUkVTX1BBU1NXT1JEJzogJ2NoYW5nZS1tZS1zdHJvbmctcGFzc3dvcmQnfSwgJ3Jlc3RhcnQnOiAndW5sZXNzLXN0b3BwZWQnLCAnaGVhbHRoY2hlY2snOiB7J3Rlc3QnOiBbJ0NNRC1TSEVMTCcsICdwZ19pc3JlYWR5IC1VIGFwcHVzZXIgLWQgYXBwZGInXSwgJ2ludGVydmFsJzogJzVzJywgJ3RpbWVvdXQnOiAnNXMnLCAncmV0cmllcyc6IDEwLCAnc3RhcnRfcGVyaW9kJzogJzEwcyd9LCAndm9sdW1lcyc6IFsncGdkYXRhOi92YXIvbGliL3Bvc3RncmVzcWwvZGF0YSddfQogaWYgbm90IGlzaW5zdGFuY2UoZGF0YS5nZXQoJ3ZvbHVtZXMnKSwgZGljdCk6IGRhdGFbJ3ZvbHVtZXMnXSA9IHt9CiBkYXRhWyd2b2x1bWVzJ11bJ3BnZGF0YSddID0ge30KIGN1ciA9IGRhdGFbJ3NlcnZpY2VzJ11bJ2Zyb250ZW5kJ10KIGlmIG5vdCBpc2luc3RhbmNlKGN1ci5nZXQoJ2RlcGVuZHNfb24nKSwgZGljdCk6IGN1clsnZGVwZW5kc19vbiddID0ge30KIGN1clsnZGVwZW5kc19vbiddWydwb3N0Z3JlcyddID0geydjb25kaXRpb24nOiAnc2VydmljZV9oZWFsdGh5J30KIGlmIG5vdCBpc2luc3RhbmNlKGN1ci5nZXQoJ2Vudmlyb25tZW50JyksIGRpY3QpOiBjdXJbJ2Vudmlyb25tZW50J10gPSB7fQogY3VyWydlbnZpcm9ubWVudCddWydEQVRBQkFTRV9VUkwnXSA9ICdwb3N0Z3Jlc3FsOi8vYXBwdXNlcjpjaGFuZ2UtbWUtc3Ryb25nLXBhc3N3b3JkQHBvc3RncmVzOjU0MzIvYXBwZGInCiBkYXRhWydzZXJ2aWNlcyddWydmcm9udGVuZCddID0gY3VyCiBpZiBub3QgZGF0YVsnc2VydmljZXMnXS5nZXQoJ3JlZGlzJyk6CiAgZGF0YVsnc2VydmljZXMnXVsncmVkaXMnXSA9IHsnaW1hZ2UnOiAncmVkaXM6Ny1hbHBpbmUnLCAnY29tbWFuZCc6ICdyZWRpcy1zZXJ2ZXIgLS1yZXF1aXJlcGFzcyBjaGFuZ2UtbWUtcmVkaXMtcGFzc3dvcmQnLCAncmVzdGFydCc6ICd1bmxlc3Mtc3RvcHBlZCcsICdoZWFsdGhjaGVjayc6IHsndGVzdCc6IFsnQ01ELVNIRUxMJywgJ3JlZGlzLWNsaSAtYSBjaGFuZ2UtbWUtcmVkaXMtcGFzc3dvcmQgcGluZyB8IGdyZXAgUE9ORyddLCAnaW50ZXJ2YWwnOiAnNXMnLCAndGltZW91dCc6ICc1cycsICdyZXRyaWVzJzogMTAsICdzdGFydF9wZXJpb2QnOiAnMTBzJ30sICd2b2x1bWVzJzogWydyZWRpc2RhdGE6L2RhdGEnXX0KIGlmIG5vdCBpc2luc3RhbmNlKGRhdGEuZ2V0KCd2b2x1bWVzJyksIGRpY3QpOiBkYXRhWyd2b2x1bWVzJ10gPSB7fQogZGF0YVsndm9sdW1lcyddWydyZWRpc2RhdGEnXSA9IHt9CiBjdXIgPSBkYXRhWydzZXJ2aWNlcyddWydmcm9udGVuZCddCiBpZiBub3QgaXNpbnN0YW5jZShjdXIuZ2V0KCdkZXBlbmRzX29uJyksIGRpY3QpOiBjdXJbJ2RlcGVuZHNfb24nXSA9IHt9CiBjdXJbJ2RlcGVuZHNfb24nXVsncmVkaXMnXSA9IHsnY29uZGl0aW9uJzogJ3NlcnZpY2VfaGVhbHRoeSd9CiBpZiBub3QgaXNpbnN0YW5jZShjdXIuZ2V0KCdlbnZpcm9ubWVudCcpLCBkaWN0KTogY3VyWydlbnZpcm9ubWVudCddID0ge30KIGN1clsnZW52aXJvbm1lbnQnXVsnUkVESVNfVVJMJ10gPSAncmVkaXM6Ly86Y2hhbmdlLW1lLXJlZGlzLXBhc3N3b3JkQHJlZGlzOjYzNzknCiBkYXRhWydzZXJ2aWNlcyddWydmcm9udGVuZCddID0gY3VyCiB3aXRoIG9wZW4ocGF0aCwgJ3cnKSBhcyBmOiB5YW1sLmR1bXAoZGF0YSwgZiwgZGVmYXVsdF9mbG93X3N0eWxlPUZhbHNlKQogcHJpbnQoJ1tkZXZwaWxvdF0gd3JpdHRlbiB0byAnICsgcGF0aCkKIHByaW50KCdmcm9udGVuZCAtPiBwYXYzMC93ZWJ2b3J5LWludGVybi1mcm9udGVuZDonICsgdGFnKQpmaW5hbGx5OgogZmNudGwuZmxvY2sobGYsIGZjbnRsLkxPQ0tfVU4pCiBsZi5jbG9zZSgp\" | base64 -d > /tmp/devpilot_frontend.py"
                                PREV_TAG=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.221.68.17 "grep 'image: pav30/webvory-intern-frontend:' ~/devpilot-app/docker-compose.yml 2>/dev/null | awk '{print \$NF}' | head -1 || echo ''")
                                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=30 ubuntu@54.221.68.17 "python3 /tmp/devpilot_frontend.py ${BUILD_NUMBER}-${BRANCH_TAG}"
                                COMPOSE_CMD=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.221.68.17 "docker compose version >/dev/null 2>&1 && echo 'docker compose' || echo 'docker-compose'")
                                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=60 ubuntu@54.221.68.17 "cd ~/devpilot-app && $COMPOSE_CMD pull frontend && $COMPOSE_CMD up -d" || {
                                    echo "Deploy failed — rolling back to $PREV_TAG"
                                    [ -n "$PREV_TAG" ] && ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.221.68.17 "sed -i 's|image: pav30/webvory-intern-frontend:.*|image: $PREV_TAG|' ~/devpilot-app/docker-compose.yml && cd ~/devpilot-app && $COMPOSE_CMD up -d" || true
                                    exit 1
                                }
                                echo "Deployed frontend to http://54.221.68.17"
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