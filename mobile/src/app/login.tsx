import { useState } from "react";
import {
  Alert,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { router } from "expo-router";
import { Colors } from "../constants/colors";
import { login, register } from "../services/api";

export default function LoginScreen() {
  const [workerId, setWorkerId] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [organization, setOrganization] = useState("");
  async function submit() {
    if (!workerId.trim() || !password)
      return Alert.alert(
        "Missing details",
        "Enter your worker ID and password.",
      );
    if (mode === "register" && (!name.trim() || !organization.trim()))
      return Alert.alert(
        "Missing details",
        "Enter your name and organisation.",
      );
    try {
      setBusy(true);
      if (mode === "register") {
        await register({
          name: name.trim(),
          worker_id: workerId.trim(),
          password,
          organization: organization.trim(),
        });
        setMode("login");
        setPassword("");
        Alert.alert(
          "Registration successful",
          "Sign in with your worker ID and PIN to continue.",
        );
        return;
      }
      await login(workerId.trim(), password);
      router.replace("/");
    } catch (error) {
      Alert.alert(
        mode === "register" ? "Registration failed" : "Sign in failed",
        error instanceof Error ? error.message : "Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.card}>
        <Text style={styles.eyebrow}>FIELD ACTIVITY LOGGER SYSTEM</Text>
        <Text style={styles.title}>
          {mode === "login" ? "Welcome back" : "Create your account"}
        </Text>
        <Text style={styles.subtitle}>
          {mode === "login"
            ? "Sign in with your worker ID to continue."
            : "Register your field worker account."}
        </Text>
        <View style={styles.tabs}>
          <TouchableOpacity onPress={() => setMode("login")}>
            <Text style={mode === "login" ? styles.activeTab : styles.tab}>
              Sign in
            </Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setMode("register")}>
            <Text style={mode === "register" ? styles.activeTab : styles.tab}>
              Register
            </Text>
          </TouchableOpacity>
        </View>
        {mode === "register" && (
          <>
            <Text style={styles.label}>Full name</Text>
            <TextInput
              style={styles.input}
              value={name}
              onChangeText={setName}
              autoComplete="name"
              placeholder="Your name"
            />
          </>
        )}
        <Text style={styles.label}>Worker ID</Text>
        <TextInput
          style={styles.input}
          value={workerId}
          onChangeText={setWorkerId}
          autoCapitalize="none"
          autoComplete="username"
          placeholder="Enter your worker ID"
        />
        <Text style={styles.label}>4 digit PIN</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={(value) =>
            setPassword(value.replace(/\D/g, "").slice(0, 4))
          }
          keyboardType="number-pad"
          maxLength={4}
          secureTextEntry
          autoComplete="password"
          placeholder="Enter 4 digits"
        />
        {mode === "register" && (
          <>
            <Text style={styles.label}>Organisation</Text>
            <TextInput
              style={styles.input}
              value={organization}
              onChangeText={setOrganization}
              placeholder="Your organisation"
            />
          </>
        )}
        <TouchableOpacity
          style={styles.button}
          disabled={busy}
          onPress={submit}
        >
          <Text style={styles.buttonText}>
            {busy
              ? "Please wait…"
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </Text>
        </TouchableOpacity>
        {/* <Text style={styles.note}>
          Administrator accounts are provisioned by your system administrator.
        </Text> */}
      </View>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  safe: {
    flex: 1,
    justifyContent: "center",
    padding: 24,
    backgroundColor: "#F4F8F9",
  },
  card: {
    backgroundColor: "white",
    borderRadius: 22,
    padding: 26,
    elevation: 3,
  },
  eyebrow: {
    color: Colors.primary,
    fontWeight: "800",
    letterSpacing: 1.4,
    marginBottom: 18,
  },
  title: { color: "#172B32", fontWeight: "800", fontSize: 29 },
  subtitle: { color: "#71838A", marginTop: 8, marginBottom: 20 },
  tabs: {
    flexDirection: "row",
    justifyContent: "space-around",
    backgroundColor: "#F0F4F4",
    borderRadius: 10,
    padding: 10,
    marginBottom: 20,
  },
  tab: { color: "#71838A", padding: 5 },
  activeTab: { color: Colors.primary, fontWeight: "800", padding: 5 },
  label: { fontWeight: "700", color: "#34464C", marginBottom: 7 },
  input: {
    borderWidth: 1,
    borderColor: "#DCE7E9",
    borderRadius: 10,
    padding: 14,
    marginBottom: 18,
    color: "#172B32",
  },
  button: {
    borderRadius: 11,
    backgroundColor: Colors.primary,
    padding: 15,
    alignItems: "center",
    marginTop: 4,
  },
  buttonText: { color: "white", fontWeight: "800" },
  note: {
    color: "#71838A",
    fontSize: 12,
    lineHeight: 18,
    marginTop: 18,
    textAlign: "center",
  },
});
