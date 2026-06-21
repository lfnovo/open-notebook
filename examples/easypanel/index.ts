import {
  Output,
  randomPassword,
  randomString,
  Services,
} from "~templates-utils";
import { Input } from "./meta";

export function generate(input: Input): Output {
  const services: Services = [];
  const appPassword = input.appPassword || randomPassword();
  const databasePassword = randomPassword();
  const encryptionKey = randomString(64);

  services.push({
    type: "app",
    data: {
      serviceName: input.databaseServiceName,
      env: [`SURREAL_EXPERIMENTAL_GRAPHQL=true`].join("\n"),
      source: {
        type: "image",
        image: input.databaseServiceImage,
      },
      deploy: {
        command: [
          "start",
          "--log info",
          "--user root",
          `--pass ${databasePassword}`,
          "--bind 0.0.0.0:8000",
          "rocksdb:/mydata/mydatabase.db",
        ].join(" "),
      },
      mounts: [
        {
          type: "volume",
          name: "surreal-data",
          mountPath: "/mydata",
        },
      ],
    },
  });

  services.push({
    type: "app",
    data: {
      serviceName: input.appServiceName,
      env: [
        `API_URL=https://$(PRIMARY_DOMAIN)`,
        `INTERNAL_API_URL=http://localhost:5055`,
        `OPEN_NOTEBOOK_ENCRYPTION_KEY=${encryptionKey}`,
        `OPEN_NOTEBOOK_PASSWORD=${appPassword}`,
        `SURREAL_URL=ws://$(PROJECT_NAME)_${input.databaseServiceName}:8000/rpc`,
        `SURREAL_USER=root`,
        `SURREAL_PASSWORD=${databasePassword}`,
        `SURREAL_NAMESPACE=open_notebook`,
        `SURREAL_DATABASE=open_notebook`,
      ].join("\n"),
      source: {
        type: "image",
        image: input.appServiceImage,
      },
      domains: [
        {
          host: "$(EASYPANEL_DOMAIN)",
          port: 8502,
        },
      ],
      mounts: [
        {
          type: "volume",
          name: "notebook-data",
          mountPath: "/app/data",
        },
      ],
    },
  });

  return { services };
}
