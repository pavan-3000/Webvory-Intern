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

        stage('Push to Registry') {
            when { expression { return fileExists('Dockerfile') } }
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    script {
                        withCredentials([usernamePassword(credentialsId: 'devpilot-registry-1782053771939', usernameVariable: 'REG_USER', passwordVariable: 'REG_PASS')]) {
                            sh '''
                                BRANCH_TAG=$(echo ${GIT_BRANCH:-${BRANCH_NAME:-main}} | sed 's|origin/||' | tr '/' '-' | tr '[:upper:]' '[:lower:]')
                                echo $REG_PASS | docker login -u $REG_USER --password-stdin
                                docker tag $DOCKER_IMAGE:$DOCKER_TAG pav30/webvory-intern-fontend:$DOCKER_TAG-$BRANCH_TAG
                                docker push pav30/webvory-intern-fontend:$DOCKER_TAG-$BRANCH_TAG || echo 'Push to registry failed!'
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
                                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.159.57.103 "echo $REG_PASS_B64 | base64 -d | docker login -u $REG_USER --password-stdin"
                                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.159.57.103 "mkdir -p ~/devpilot-app && echo 'IyBBcHBsaWNhdGlvbgpBUFBfRU5WPXByb2R1Y3Rpb24KQVBQX1NFQ1JFVF9LRVk9Y2hhbmdlLW1lLXRvLWEtcmFuZG9tLXNlY3JldC1rZXktYXQtbGVhc3QtMzItY2hhcnMKQVBQX0RFQlVHPWZhbHNlCkFQUF9QT1JUPTgwMDAKCiMgUG9zdGdyZVNRTApQT1NUR1JFU19IT1NUPWRiClBPU1RHUkVTX1BPUlQ9NTQzMgpQT1NUR1JFU19EQj1hcHBkYgpQT1NUR1JFU19VU0VSPWFwcHVzZXIKUE9TVEdSRVNfUEFTU1dPUkQ9Y2hhbmdlLW1lLXN0cm9uZy1wYXNzd29yZAoKRE9NQUlOPXdlYnZvcnktaW50ZXJu' | base64 -d > ~/devpilot-app/fontend.env"
                                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.159.57.103 "pip3 install pyyaml -q 2>/dev/null || true; echo \"aW1wb3J0IHlhbWwsIHN5cywgb3MsIGZjbnRsCnBhdGggPSBvcy5wYXRoLmV4cGFuZHVzZXIoJ34vZGV2cGlsb3QtYXBwL2RvY2tlci1jb21wb3NlLnltbCcpCnRhZyA9IHN5cy5hcmd2WzFdCm9zLm1ha2VkaXJzKG9zLnBhdGguZXhwYW5kdXNlcignfi9kZXZwaWxvdC1hcHAnKSwgZXhpc3Rfb2s9VHJ1ZSkKbGYgPSBvcGVuKG9zLnBhdGguZXhwYW5kdXNlcignfi9kZXZwaWxvdC1hcHAvLmRldnBpbG90LmxvY2snKSwgJ3cnKQpmY250bC5mbG9jayhsZiwgZmNudGwuTE9DS19FWCkKdHJ5OgogdHJ5OgogIHdpdGggb3BlbihwYXRoKSBhcyBmOiBkYXRhID0geWFtbC5zYWZlX2xvYWQoZikgb3Ige30KIGV4Y2VwdCBFeGNlcHRpb246CiAgZGF0YSA9IHt9CiBpZiBub3QgaXNpbnN0YW5jZShkYXRhLmdldCgnc2VydmljZXMnKSwgZGljdCk6IGRhdGFbJ3NlcnZpY2VzJ10gPSB7fQogZXhpc3RpbmcgPSBkYXRhWydzZXJ2aWNlcyddLmdldCgnZm9udGVuZCcpCiBwcmludCgnW2RldnBpbG90XSBzZXJ2aWNlPWZvbnRlbmQgZXhpc3Rpbmc9JyArIHN0cihleGlzdGluZyBpcyBub3QgTm9uZSkpCiBpZiBleGlzdGluZzoKICBwcmludCgnW2RldnBpbG90XSBvbGQgaW1hZ2U9JyArIHN0cihleGlzdGluZy5nZXQoJ2ltYWdlJykpICsgJyBvbGQgcG9ydHM9JyArIHN0cihleGlzdGluZy5nZXQoJ3BvcnRzJykpKQogIGV4aXN0aW5nWydpbWFnZSddID0gJ3BhdjMwL3dlYnZvcnktaW50ZXJuLWZvbnRlbmQ6JyArIHRhZwogIGV4aXN0aW5nWydjb250YWluZXJfbmFtZSddID0gJ2ZvbnRlbmQnCiAgZXhpc3RpbmdbJ3BvcnRzJ10gPSBbJzgwMDA6ODAwMCddCiAgcHJpbnQoJ1tkZXZwaWxvdF0gbmV3IGltYWdlPScgKyBleGlzdGluZ1snaW1hZ2UnXSArICcgbmV3IHBvcnRzPScgKyBzdHIoZXhpc3RpbmcuZ2V0KCdwb3J0cycpKSkKICBkYXRhWydzZXJ2aWNlcyddWydmb250ZW5kJ10gPSBleGlzdGluZwogZWxzZToKICBwcmludCgnW2RldnBpbG90XSBjcmVhdGluZyBuZXcgc2VydmljZSBibG9jaycpCiAgc3ZjID0geydpbWFnZSc6ICdwYXYzMC93ZWJ2b3J5LWludGVybi1mb250ZW5kOicgKyB0YWcsICdjb250YWluZXJfbmFtZSc6ICdmb250ZW5kJywgJ3Jlc3RhcnQnOiAndW5sZXNzLXN0b3BwZWQnfQogIHN2Y1sncG9ydHMnXSA9IFsnODAwMDo4MDAwJ10KICBzdmNbJ2Vudl9maWxlJ10gPSBbJ34vZGV2cGlsb3QtYXBwL2ZvbnRlbmQuZW52J10KICBwcmludCgnW2RldnBpbG90XSBuZXcgc2VydmljZSBwb3J0cz0nICsgc3RyKHN2Yy5nZXQoJ3BvcnRzJykpKQogIGRhdGFbJ3NlcnZpY2VzJ11bJ2ZvbnRlbmQnXSA9IHN2YwogaWYgbm90IGRhdGFbJ3NlcnZpY2VzJ10uZ2V0KCdkYicpOgogIGRhdGFbJ3NlcnZpY2VzJ11bJ2RiJ10gPSB7J2ltYWdlJzogJ3Bvc3RncmVzOjE2LWFscGluZScsICdlbnZpcm9ubWVudCc6IHsnUE9TVEdSRVNfREInOiAnZGInLCAnUE9TVEdSRVNfVVNFUic6ICdhcHB1c2VyJywgJ1BPU1RHUkVTX1BBU1NXT1JEJzogJ2NoYW5nZS1tZS1zdHJvbmctcGFzc3dvcmQnfSwgJ3Jlc3RhcnQnOiAndW5sZXNzLXN0b3BwZWQnLCAnaGVhbHRoY2hlY2snOiB7J3Rlc3QnOiBbJ0NNRC1TSEVMTCcsICdwZ19pc3JlYWR5IC1VIGFwcHVzZXIgLWQgZGInXSwgJ2ludGVydmFsJzogJzVzJywgJ3RpbWVvdXQnOiAnNXMnLCAncmV0cmllcyc6IDEwLCAnc3RhcnRfcGVyaW9kJzogJzEwcyd9LCAndm9sdW1lcyc6IFsncGdkYXRhOi92YXIvbGliL3Bvc3RncmVzcWwvZGF0YSddfQogaWYgbm90IGlzaW5zdGFuY2UoZGF0YS5nZXQoJ3ZvbHVtZXMnKSwgZGljdCk6IGRhdGFbJ3ZvbHVtZXMnXSA9IHt9CiBkYXRhWyd2b2x1bWVzJ11bJ3BnZGF0YSddID0ge30KIGN1ciA9IGRhdGFbJ3NlcnZpY2VzJ11bJ2ZvbnRlbmQnXQogaWYgbm90IGlzaW5zdGFuY2UoY3VyLmdldCgnZGVwZW5kc19vbicpLCBkaWN0KTogY3VyWydkZXBlbmRzX29uJ10gPSB7fQogY3VyWydkZXBlbmRzX29uJ11bJ2RiJ10gPSB7J2NvbmRpdGlvbic6ICdzZXJ2aWNlX2hlYWx0aHknfQogaWYgbm90IGlzaW5zdGFuY2UoY3VyLmdldCgnZW52aXJvbm1lbnQnKSwgZGljdCk6IGN1clsnZW52aXJvbm1lbnQnXSA9IHt9CiBjdXJbJ2Vudmlyb25tZW50J11bJ0RBVEFCQVNFX1VSTCddID0gJ3Bvc3RncmVzcWw6Ly9hcHB1c2VyOmNoYW5nZS1tZS1zdHJvbmctcGFzc3dvcmRAZGI6NTQzMi9kYicKIGRhdGFbJ3NlcnZpY2VzJ11bJ2ZvbnRlbmQnXSA9IGN1cgogd2l0aCBvcGVuKHBhdGgsICd3JykgYXMgZjogeWFtbC5kdW1wKGRhdGEsIGYsIGRlZmF1bHRfZmxvd19zdHlsZT1GYWxzZSkKIHByaW50KCdbZGV2cGlsb3RdIHdyaXR0ZW4gdG8gJyArIHBhdGgpCiBwcmludCgnZm9udGVuZCAtPiBwYXYzMC93ZWJ2b3J5LWludGVybi1mb250ZW5kOicgKyB0YWcpCmZpbmFsbHk6CiBmY250bC5mbG9jayhsZiwgZmNudGwuTE9DS19VTikKIGxmLmNsb3NlKCk=\" | base64 -d > /tmp/devpilot_fontend.py"
                                PREV_TAG=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.159.57.103 "grep 'image: pav30/webvory-intern-fontend:' ~/devpilot-app/docker-compose.yml 2>/dev/null | awk '{print \$NF}' | head -1 || echo ''")
                                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.159.57.103 "python3 /tmp/devpilot_fontend.py ${BUILD_NUMBER}-${BRANCH_TAG}"
                                COMPOSE_CMD=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.159.57.103 "docker compose version >/dev/null 2>&1 && echo 'docker compose' || echo 'docker-compose'")
                                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=60 ubuntu@54.159.57.103 "cd ~/devpilot-app && $COMPOSE_CMD pull fontend && $COMPOSE_CMD up -d --no-deps fontend" || {
                                    echo "Deploy failed — rolling back to $PREV_TAG"
                                    [ -n "$PREV_TAG" ] && ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 ubuntu@54.159.57.103 "sed -i 's|image: pav30/webvory-intern-fontend:.*|image: $PREV_TAG|' ~/devpilot-app/docker-compose.yml && cd ~/devpilot-app && $COMPOSE_CMD up -d --no-deps fontend" || true
                                    exit 1
                                }
                                echo "Deployed fontend to http://54.159.57.103"
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