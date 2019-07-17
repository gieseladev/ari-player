workflow "Publish Docker image on release" {
  resolves = [
    "Docker push latest",
    "Docker push version",
    "Docker push SHA",
  ]
  on = "create"
}

action "Filter version tags" {
  uses = "actions/bin/filter@master"
  args = "tag v*"
}

action "Docker login" {
  uses = "actions/docker/login@master"
  needs = ["Filter version tags"]
  secrets = ["DOCKER_PASSWORD", "DOCKER_USERNAME"]
}

action "Docker build" {
  uses = "actions/docker/cli@master"
  needs = ["Docker login"]
  args = "build --tag ari ."
}

action "Docker tag" {
  uses = "actions/docker/tag@master"
  needs = ["Docker build"]
  args = "--env ari gieseladev/ari"
}

action "Docker push latest" {
  uses = "actions/docker/cli@master"
  needs = ["Docker tag"]
  args = "push gieseladev/ari:latest"
}

action "Docker push version" {
  uses = "actions/docker/cli@master"
  needs = ["Docker tag"]
  args = "push gieseladev/ari:$IMAGE_REF"
}

action "Docker push SHA" {
  uses = "actions/docker/cli@master"
  needs = ["Docker tag"]
  args = "push gieseladev/ari:$IMAGE_SHA"
}
