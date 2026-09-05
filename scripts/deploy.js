const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Deploying EvidenceRegistry contract...");

  const EvidenceRegistry = await hre.ethers.getContractFactory("EvidenceRegistry");
  const registry = await EvidenceRegistry.deploy();

  await registry.waitForDeployment();
  const address = await registry.getAddress();

  console.log(`✓ EvidenceRegistry deployed to address: ${address}`);

  // Save address to deployment.json artifact
  const artifactsDir = path.join(__dirname, "..", "artifacts");
  if (!fs.existsSync(artifactsDir)) {
    fs.mkdirSync(artifactsDir, { recursive: true });
  }

  const deploymentData = {
    contractAddress: address,
    network: hre.network.name,
    timestamp: new Date().toISOString()
  };

  fs.writeFileSync(
    path.join(artifactsDir, "deployment.json"),
    JSON.stringify(deploymentData, null, 2)
  );

  // Update .env file CONTRACT_ADDRESS
  const envPath = path.join(__dirname, "..", ".env");
  if (fs.existsSync(envPath)) {
    let envContent = fs.readFileSync(envPath, "utf-8");
    if (envContent.includes("CONTRACT_ADDRESS=")) {
      envContent = envContent.replace(/CONTRACT_ADDRESS=.*/, `CONTRACT_ADDRESS=${address}`);
    } else {
      envContent += `\nCONTRACT_ADDRESS=${address}`;
    }
    fs.writeFileSync(envPath, envContent);
    console.log(`✓ Updated CONTRACT_ADDRESS in .env to ${address}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
